import chainlit as cl
from typing import List
from chainlit.input_widget import Select
from gemini_backend import get_gemini_backend
from pdf_parser import get_pdf_parser
from pdf_db_service import (
    list_pdf_names,
    get_pdf_bytes,
    save_pdf_bytes,
    extract_text_and_layout,
    regenerate_pdf_with_layout,
    write_preview_pdf,
)
from queries import compare_fd_pi, save_documents_to_files, check_vague_content_and_bibliography

# Store uploaded PDFs in session
pdf_documents: List[dict] = []


def _is_pdf_element(el) -> bool:
    return hasattr(el, "name") and isinstance(el.name, str) and el.name.lower().endswith(".pdf")


@cl.on_chat_start
async def start():
    """Initialize the chat session and display the PDF import interface."""
    await cl.Message(
        content=(
            "🎓 **Bun venit la Sistem de Validare Curriculumi!**\n\n"
            "Încarcă **exact 2 documente PDF** în același mesaj:\n"
            "1️⃣ **Fișa Disciplinei (FD)**\n"
            "2️⃣ **Planul de Învățământ (PI)**\n\n"
            "După încărcare, sistemul va parse ambele documente și îți va oferi opțiuni de validare și analiză."
        )
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    global pdf_documents

    gemini = get_gemini_backend()
    parser = get_pdf_parser()

    # If no file elements, ask user to upload
    if not message.elements:
        await cl.Message(content="📁 Te rog, încarcă 2 documente PDF (FD apoi PI) în același mesaj.").send()
        return

    pdf_files = [el for el in message.elements if _is_pdf_element(el)]

    if len(pdf_files) != 2:
        await cl.Message(content="❌ Te rog, încarcă **exact 2** documente PDF în același mesaj (mai întâi FD, apoi PI)." ).send()
        return

    # FD is first, PI is second (as requested)
    fd_file, pi_file = pdf_files[0], pdf_files[1]

    pdf_documents = []

    async def _parse_and_store(file_el, role: str):
        pdf_path = getattr(file_el, 'path', None) or getattr(file_el, 'local_path', None) or file_el.name
        result = parser.parse_pdf(pdf_path)
        if not result or not result.get("success"):
            raise RuntimeError(result.get("error") or "Unknown parse error")

        doc = {
            "role": role,  # 'FD' or 'PI'
            "name": file_el.name,
            "path": pdf_path,
            "pages": result.get("page_count"),
            "full_text": result.get("text") or "",
            "is_scanned": result.get("is_scanned"),
            "extraction_method": result.get("method"),
        }
        pdf_documents.append(doc)

        doc_type = "🖼️ Scanned (OCR)" if doc["is_scanned"] else "📄 Regular Text"
        await cl.Message(
            content=(
                f"✅ Imported **{role}**: **{doc['name']}**\n"
                f"- Pages: {doc['pages']}\n"
                f"- Type: {doc_type}\n"
                f"- Extraction: {doc['extraction_method']}\n"
                f"- Preview: {(doc['full_text'][:200] + '...') if doc['full_text'] else 'No text'}"
            )
        ).send()

        return doc

    try:
        fd_doc = await _parse_and_store(fd_file, "FD")
        pi_doc = await _parse_and_store(pi_file, "PI")

        # Save immediately to fd.txt / pi.txt
        save_res = save_documents_to_files(fd_doc["full_text"], pi_doc["full_text"], "fd.txt", "pi.txt")
        if save_res.get("success"):
            await cl.Message(
                content=(
                    "💾 Saved parsed text files:\n"
                    f"- fd.txt ({save_res.get('fd_size',0)} chars)\n"
                    f"- pi.txt ({save_res.get('pi_size',0)} chars)"
                )
            ).send()
        else:
            await cl.Message(content=f"⚠️ Could not save fd.txt/pi.txt: {save_res.get('error')}").send()

        # Buttons: verify each + compare (with Romanian labels)
        actions = [
            cl.Action(
                name="verify_parser",
                value=fd_doc["name"],
                description="🔍 Verifică Fișa Disciplinei",
                payload={"pdf_name": fd_doc["name"]},
            ),
            cl.Action(
                name="verify_parser",
                value=pi_doc["name"],
                description="🔍 Verifică Planul de Învățământ",
                payload={"pdf_name": pi_doc["name"]},
            ),
            cl.Action(
                name="compare_fd_pi",
                value="compare",
                description="📊 Compară FD cu PI",
                payload={"doc1_idx": 0, "doc2_idx": 1},
            ),
            cl.Action(
                name="check_components",
                value=fd_doc["name"],
                description="✅ Validare componente FD",
                payload={"pdf_name": fd_doc["name"]},
            ),
            cl.Action(
                name="check_vague_content",
                value=pi_doc["name"],
                description="⚠️ Detectează conținut vag și bibliografie neactualizată",
                payload={"pdf_name": pi_doc["name"]},
            ),
        ]

        await cl.Message(
            content=(
                "✅ **Gata!** Alege una din opțiunile de validare de mai jos:\n\n"
                "- **Verifică Fișa Disciplinei**: Parse și analiză FD\n"
                "- **Verifică Planul de Învățământ**: Parse și analiză PI\n"
                "- **Compară FD cu PI**: Raport detaliat de inconsistențe\n"
                "- **Validare componente FD**: Verificare matematică și structură\n"
                "- **Detectează conținut vag**: Analiză bibliografie și claritate"
            ),
            actions=actions,
        ).send()

    except Exception as e:
        await cl.Message(content=f"❌ Error parsing PDFs: {str(e)}").send()
        return


async def _send_db_pdf_actions(pdf_name: str):
    await cl.Message(
        content=f"**{pdf_name}**",
        actions=[
            cl.Action(
                name="view_db_pdf",
                value=pdf_name,
                description="Vizualizeaza",
                payload={"pdf_name": pdf_name},
            ),
            cl.Action(
                name="edit_db_pdf",
                value=pdf_name,
                description="Editeaza si salveaza",
                payload={"pdf_name": pdf_name},
            ),
        ],
    ).send()


@cl.action_callback("open_db_dropdown")
async def open_db_dropdown_action(_action: cl.Action):
    """Open a dropdown with all PDF names from PostgreSQL."""
    try:
        names = list_pdf_names()
    except Exception as exc:
        await cl.Message(content=f"❌ Nu am putut citi baza de date: {str(exc)}").send()
        return

    if not names:
        await cl.Message(content="ℹ️ Nu exista PDF-uri in baza de date.").send()
        return

    cl.user_session.set("db_pdf_names", names)

    await cl.ChatSettings(
        [
            Select(
                id="db_pdf_selected",
                label="Selecteaza PDF-ul din PostgreSQL",
                values=names,
                initial_value=names[0],
            )
        ]
    ).send()

    await cl.Message(content="⬇️ Foloseste dropdown-ul din dreapta sus (Settings), apoi alege PDF-ul.").send()


@cl.on_settings_update
async def on_settings_update(settings: dict):
    """Handle dropdown selection updates for DB PDFs."""
    selected = settings.get("db_pdf_selected")
    available = cl.user_session.get("db_pdf_names") or []

    if selected and selected in available:
        await _send_db_pdf_actions(selected)


@cl.action_callback("list_db_pdfs")
async def list_db_pdfs_action(_action: cl.Action):
    """List PDFs stored in PostgreSQL and expose view/edit actions."""
    try:
        names = list_pdf_names()
    except Exception as exc:
        await cl.Message(content=f"❌ Nu am putut citi baza de date: {str(exc)}").send()
        return

    if not names:
        await cl.Message(content="ℹ️ Nu exista PDF-uri in baza de date.").send()
        return

    await cl.Message(content=f"📚 Am gasit {len(names)} PDF-uri in baza de date.").send()

    for name in names:
        await _send_db_pdf_actions(name)


@cl.action_callback("view_db_pdf")
async def view_db_pdf_action(action: cl.Action):
    """Render a PDF from DB directly in chat."""
    pdf_name = action.payload.get("pdf_name") if action.payload else None
    if not pdf_name:
        await cl.Message(content="❌ Numele PDF-ului lipseste.").send()
        return

    try:
        pdf_bytes = get_pdf_bytes(pdf_name)
        if not pdf_bytes:
            await cl.Message(content=f"❌ PDF inexistent in baza de date: {pdf_name}").send()
            return

        preview_path = write_preview_pdf(pdf_name, pdf_bytes, suffix="_view")
        await cl.Message(
            content=f"📄 Vizualizare: **{pdf_name}**",
            elements=[cl.Pdf(name=pdf_name, path=preview_path, display="inline")],
        ).send()
    except Exception as exc:
        await cl.Message(content=f"❌ Eroare la vizualizare: {str(exc)}").send()


@cl.action_callback("edit_db_pdf")
async def edit_db_pdf_action(action: cl.Action):
    """Prepare DB PDF for text edit and wait for user edited content."""
    pdf_name = action.payload.get("pdf_name") if action.payload else None
    if not pdf_name:
        await cl.Message(content="❌ Numele PDF-ului lipseste.").send()
        return

    try:
        pdf_bytes = get_pdf_bytes(pdf_name)
        if not pdf_bytes:
            await cl.Message(content=f"❌ PDF inexistent in baza de date: {pdf_name}").send()
            return

        text, templates = extract_text_and_layout(pdf_bytes)
        cl.user_session.set(
            "pending_db_edit",
            {
                "pdf_name": pdf_name,
                "original_pdf": pdf_bytes,
                "templates": templates,
            },
        )

        preview = text[:1200] + ("..." if len(text) > 1200 else "")
        await cl.Message(
            content=(
                f"✏️ **Editare pregatita pentru:** {pdf_name}\n\n"
                "Trimite acum textul editat in urmatorul mesaj.\n"
                "Scrie `/cancel` daca vrei sa anulezi.\n\n"
                f"Preview text curent:\n\n{preview}"
            )
        ).send()
    except Exception as exc:
        await cl.Message(content=f"❌ Eroare la pregatirea editarii: {str(exc)}").send()


@cl.action_callback("verify_parser")
async def verify_parser_action(action: cl.Action):
    """Handle parser verification button click."""
    parser = get_pdf_parser()

    try:
        # Get pdf_name from payload
        pdf_name = action.payload.get("pdf_name") if action.payload else None

        if not pdf_name:
            await cl.Message(content="❌ Error: PDF name not found").send()
            return

        # Find the matching PDF
        matching_pdf = next((pdf for pdf in pdf_documents if pdf['name'] == pdf_name), None)

        if not matching_pdf:
            await cl.Message(content=f"❌ PDF not found: {pdf_name}").send()
            return

        # Re-parse the PDF
        parse_result = parser.parse_pdf(matching_pdf['path'])

        if parse_result and parse_result.get('success') and parse_result.get('text'):
            # Save directly to output.txt (just the raw text)
            with open("output.txt", 'w', encoding='utf-8') as f:
                f.write(parse_result.get('text') or "")

            # Send success message
            msg = (
                f"✅ Parser Verification Complete!\n\n"
                f"File: {matching_pdf['name']}\n"
                f"Pages: {parse_result.get('page_count')}\n"
                f"Type: {'Scanned (OCR)' if parse_result.get('is_scanned') else 'Regular Text'}\n\n"
                f"✅ output.txt created with {len(parse_result.get('text') or '')} characters"
            )

            await cl.Message(content=msg).send()
        else:
            await cl.Message(content=f"❌ Failed to parse PDF: {parse_result.get('error') if parse_result else 'No result'}").send()

    except Exception as e:
        print(f"ERROR in verify_parser_action: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Error: {str(e)}").send()


@cl.action_callback("check_components")
async def check_components_action(action: cl.Action):
    """Handle check missing components button click."""
    gemini = get_gemini_backend()

    try:
        # Get pdf_name from payload
        pdf_name = action.payload.get("pdf_name") if action.payload else None

        if not pdf_name:
            await cl.Message(content="❌ Error: PDF name not found").send()
            return

        # Find the matching PDF
        matching_pdf = next((pdf for pdf in pdf_documents if pdf['name'] == pdf_name), None)

        if not matching_pdf:
            await cl.Message(content=f"❌ PDF not found: {pdf_name}").send()
            return

        if not matching_pdf['full_text']:
            await cl.Message(content="❌ No text available for analysis").send()
            return

        # Show loading message
        await cl.Message(content="🔍 Analyzing PDF for missing components and validation...").send()

        # Check for missing components using Gemini with master prompt
        result = gemini.check_missing_components(matching_pdf['full_text'], pdf_name)

        if result.get('success'):
            analysis = result.get('analysis')

            if isinstance(analysis, dict):
                # Parse JSON response
                status = analysis.get('status', 'UNKNOWN')
                math_errors = analysis.get('math_errors', [])
                structural_errors = analysis.get('structural_errors', [])
                missing_components = analysis.get('missing_components', [])
                general_warnings = analysis.get('general_warnings', [])

                # Build formatted message
                status_icon = "✅" if status == "VALID" else "❌"
                msg = f"📊 **Academic Audit Results**\n\n**File:** {pdf_name}\n\n**Status:** {status_icon} {status}\n\n"

                # Math Errors
                if math_errors:
                    msg += "**❌ Mathematical Errors Found:**\n"
                    for error in math_errors:
                        msg += f"\n• **{error.get('rule', 'Unknown Rule')}**\n"
                        msg += f"  - Expected: {error.get('expected', 'N/A')}\n"
                        msg += f"  - Found: {error.get('found', 'N/A')}\n"
                        msg += f"  - Details: {error.get('details', 'N/A')}\n"
                else:
                    msg += "✅ **No mathematical errors found**\n"

                msg += "\n"

                # Structural Errors
                if structural_errors:
                    msg += "**⚠️ Structural Issues:**\n"
                    for error in structural_errors:
                        msg += f"\n• **{error.get('section', 'Unknown Section')}**\n"
                        msg += f"  - Issue: {error.get('issue', 'N/A')}\n"
                        msg += f"  - Details: {error.get('details', 'N/A')}\n"
                else:
                    msg += "✅ **Document structure is correct**\n"

                msg += "\n"

                # Missing Components
                if missing_components:
                    msg += "**📋 Missing Components:**\n"
                    for component in missing_components:
                        msg += f"• {component}\n"
                else:
                    msg += "✅ **All required components are present**\n"

                msg += "\n"

                # General Warnings
                if general_warnings:
                    msg += "**⚠️ General Warnings:**\n"
                    for warning in general_warnings:
                        msg += f"• {warning}\n"

                await cl.Message(content=msg).send()
            else:
                # Raw response (couldn't parse as JSON)
                msg = f"📊 **Validation Analysis**\n\n**File:** {pdf_name}\n\n**Raw Analysis:**\n{result.get('raw_response', 'No response')}"
                await cl.Message(content=msg).send()
        else:
            await cl.Message(content=f"❌ Analysis failed: {result.get('error', 'Unknown error')}").send()

    except Exception as e:
        print(f"ERROR in check_components_action: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Error: {str(e)}").send()


@cl.action_callback("compare_fd_pi")
async def compare_fd_pi_action(action: cl.Action):
    """Handle FD vs PI comparison."""
    try:
        doc1_idx = action.payload.get("doc1_idx") if action.payload else 0
        doc2_idx = action.payload.get("doc2_idx") if action.payload else 1

        if len(pdf_documents) < 2:
            await cl.Message(content="❌ Need 2 documents to compare").send()
            return

        doc1 = pdf_documents[doc1_idx]
        doc2 = pdf_documents[doc2_idx]

        # Show loading message
        await cl.Message(content=f"🔄 Comparing {doc1['name']} (FD) with {doc2['name']} (PI)...").send()

        # Get the text content
        fd_text = doc1.get('full_text') or ""
        pi_text = doc2.get('full_text') or ""

        # Save to files
        save_result = save_documents_to_files(fd_text, pi_text)

        if save_result.get('success'):
            await cl.Message(
                content=f"✅ Documents saved:\n- fd.txt ({save_result.get('fd_size',0)} chars)\n- pi.txt ({save_result.get('pi_size',0)} chars)"
            ).send()

        # Compare documents using Gemini
        comparison_result = compare_fd_pi(fd_text, pi_text)

        if comparison_result.get('success'):
            # Display the formatted text response directly
            report = comparison_result.get('analysis', 'No response')
            await cl.Message(content=report).send()
        else:
            await cl.Message(
                content=f"❌ Comparison failed: {comparison_result.get('error', 'Unknown error')}"
            ).send()

    except Exception as e:
        print(f"ERROR in compare_fd_pi_action: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Error: {str(e)}").send()


@cl.action_callback("check_vague_content")
async def check_vague_content_action(action: cl.Action):
    """Handle vague content and outdated bibliography check button click."""
    try:
        # Get pdf_name from payload
        pdf_name = action.payload.get("pdf_name") if action.payload else None

        if not pdf_name:
            await cl.Message(content="❌ Eroare: Numele PDF-ului nu a fost găsit").send()
            return

        # Find the matching PDF (should be the PI document)
        matching_pdf = next((pdf for pdf in pdf_documents if pdf['name'] == pdf_name), None)

        if not matching_pdf:
            await cl.Message(content=f"❌ PDF nu a fost găsit: {pdf_name}").send()
            return

        if not matching_pdf['full_text']:
            await cl.Message(content="❌ Nu este disponibil text pentru analiză").send()
            return

        # Show loading message
        await cl.Message(content="🔍 Se analizează conținutul vag și bibliografia...").send()

        # Check for vague content and outdated bibliography
        result = check_vague_content_and_bibliography(matching_pdf['full_text'], pdf_name)

        if result.get('success'):
            analysis = result.get('analysis')
            
            # Display the formatted text response directly
            msg = f"📋 **RAPORT - ANALIZA CONȚINUT VAG ȘI BIBLIOGRAFIE**\n\n**Fișier:** {pdf_name}\n\n{analysis}"
            await cl.Message(content=msg).send()
        else:
            await cl.Message(
                content=f"❌ Analiza a eșuat: {result.get('error', 'Eroare necunoscută')}"
            ).send()

    except Exception as e:
        print(f"ERROR in check_vague_content_action: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Eroare: {str(e)}").send()


def get_loaded_pdfs() -> List[dict]:
    """Retrieve the currently loaded PDF documents."""
    return pdf_documents


def clear_pdfs():
    """Clear all loaded PDF documents."""
    global pdf_documents
    pdf_documents = []
