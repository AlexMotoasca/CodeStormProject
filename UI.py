import chainlit as cl
import PyPDF2
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

# Store uploaded PDFs in session
pdf_documents = []


async def start():
    """Initialize the chat session and display the PDF import interface."""
    await cl.Message(
        content="Welcome! Please upload 1-2 PDF documents to get started. "
                "Use the file upload button below to select your PDF files.\n\n"
                "Features:\n"
                "✅ Auto-detect regular and scanned PDFs\n"
                "✅ Parse and extract text\n"
                "✅ Create output.txt with parsed content\n"
                "✅ AI-powered analysis with Gemini\n\n"
                "Database tools:\n"
                "- Click 'Alege PDF din baza de date' to open a dropdown with all PostgreSQL PDFs",
        actions=[
            cl.Action(
                name="open_db_dropdown",
                value="open",
                description="Alege PDF din baza de date",
                payload={"source": "welcome"},
            )
        ],
    ).send()


async def handle_message(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    global pdf_documents
    gemini = get_gemini_backend()
    parser = get_pdf_parser()

    pending_edit = cl.user_session.get("pending_db_edit")
    if pending_edit and not message.elements:
        user_text = message.content if isinstance(message.content, str) else ""
        command = user_text.strip()

        if not command:
            await cl.Message(content="⚠️ Trimite textul editat sau `/cancel`.").send()
            return

        if command.lower() == "/cancel":
            cl.user_session.set("pending_db_edit", None)
            await cl.Message(content="✅ Editarea din baza de date a fost anulata.").send()
            return

        try:
            original_pdf = pending_edit["original_pdf"]
            templates = pending_edit["templates"]
            pdf_name = pending_edit["pdf_name"]

            edited_pdf = regenerate_pdf_with_layout(original_pdf, user_text, templates)
            updated_rows = save_pdf_bytes(pdf_name, edited_pdf)

            cl.user_session.set("pending_db_edit", None)

            preview_path = write_preview_pdf(pdf_name, edited_pdf, suffix="_updated")
            await cl.Message(
                content=(
                    f"✅ PDF actualizat in baza de date: **{pdf_name}**\n"
                    f"Randuri actualizate: {updated_rows}"
                ),
                elements=[cl.Pdf(name=f"{pdf_name} (updated)", path=preview_path, display="inline")],
            ).send()
        except Exception as exc:
            await cl.Message(content=f"❌ Eroare la salvare PDF: {str(exc)}").send()

        return

    # Check if files were uploaded
    if message.elements:
        pdf_files = [file for file in message.elements if file.name.endswith('.pdf')]

        if not pdf_files:
            await cl.Message(
                content="❌ No PDF files found. Please upload PDF documents."
            ).send()
            return

        if len(pdf_files) > 2:
            await cl.Message(
                content="❌ Please upload maximum 2 PDF documents."
            ).send()
            return

        # Process uploaded PDFs
        pdf_documents = []
        for file in pdf_files:
            try:
                pdf_path = file.path

                # Use enhanced parser to extract text (handles both regular and scanned PDFs)
                parse_result = parser.parse_pdf(pdf_path)

                if not parse_result['success']:
                    error_msg = parse_result['error'] if parse_result['error'] else "Unknown error occurred"
                    await cl.Message(
                        content=f"❌ Error processing {file.name}: {error_msg}"
                    ).send()
                    continue

                # Determine if scanned
                is_scanned = parse_result['is_scanned']
                method = parse_result['method']

                pdf_documents.append({
                    'name': file.name,
                    'path': pdf_path,
                    'pages': parse_result['page_count'],
                    'preview': parse_result['text'][:200] if parse_result['text'] else "",
                    'full_text': parse_result['text'],
                    'is_scanned': is_scanned,
                    'extraction_method': method
                })

                # Confirm upload with extraction method
                method_text = "🖼️ Scanned (OCR)" if is_scanned else "📄 Regular Text"
                await cl.Message(
                    content=f"✅ Successfully imported: **{file.name}**\n"
                            f"- Pages: {parse_result['page_count']}\n"
                            f"- Type: {method_text}\n"
                            f"- Preview: {parse_result['text'][:150]}..."
                ).send()

                # Add button to verify parser functionality and create output.txt
                verify_action = cl.Action(
                    name="verify_parser",
                    value=file.name,
                    description="Verify parser and create output.txt",
                    payload={"pdf_name": file.name}
                )

                # Add button to check for missing components
                check_components_action = cl.Action(
                    name="check_components",
                    value=file.name,
                    description="Check for missing components",
                    payload={"pdf_name": file.name}
                )

                await cl.Message(
                    content=f"🔍 **Parser Actions**\n\n"
                            f"**PDF:** {file.name}\n\n"
                            f"Click buttons below:",
                    actions=[verify_action, check_components_action]
                ).send()
            except Exception as e:
                await cl.Message(
                    content=f"❌ Error processing {file.name}: {str(e)}"
                ).send()

        # If 2 PDFs are uploaded, show summary
        if len(pdf_documents) == 2:
            summary = "📊 **PDF Summary**\n\n"
            for i, pdf in enumerate(pdf_documents, 1):
                doc_type = "🖼️ Scanned" if pdf['is_scanned'] else "📄 Regular"
                summary += f"**Document {i}: {pdf['name']}**\n"
                summary += f"- Pages: {pdf['pages']}\n"
                summary += f"- Type: {doc_type}\n"
                summary += f"- Extraction: {pdf['extraction_method']}\n\n"

            summary += "✨ Both documents are ready for processing!\n\n"
            summary += "You can now:\n"
            summary += "- Ask questions about the documents\n"
            summary += "- Request summaries\n"
            summary += "- Compare documents\n"
            summary += "- Extract specific information"

            await cl.Message(content=summary).send()

        elif len(pdf_documents) == 1:
            await cl.Message(
                content="ℹ️ 1 document uploaded. You can upload 1 more PDF document or continue with analysis."
            ).send()
    else:
        # Handle text messages with Gemini
        if pdf_documents:
            content = message.content if isinstance(message.content, str) else ""
            user_input = content.strip().lower()

            # Summarize command
            if "summarize" in user_input or "summary" in user_input:
                await cl.Message(content="📝 Generating summary...").send()
                for i, pdf in enumerate(pdf_documents, 1):
                    summary = gemini.summarize_pdf(pdf['full_text'])
                    await cl.Message(
                        content=f"**Summary of {pdf['name']}:**\n\n{summary}"
                    ).send()

            # Compare documents
            elif "compare" in user_input and len(pdf_documents) == 2:
                await cl.Message(content="🔍 Comparing documents...").send()
                comparison = gemini.compare_pdfs(
                    pdf_documents[0]['full_text'],
                    pdf_documents[1]['full_text']
                )
                await cl.Message(
                    content=f"**Comparison Result:**\n\n{comparison}"
                ).send()

            # General questions
            else:
                await cl.Message(content="🤔 Analyzing documents...").send()

                # Combine PDFs for analysis
                combined_text = "\n\n---\n\n".join([
                    f"Document: {pdf['name']}\n{pdf['full_text']}"
                    for pdf in pdf_documents
                ])

                analysis = gemini.analyze_pdf_content(combined_text, content)
                await cl.Message(
                    content=f"**Analysis:**\n\n{analysis}"
                ).send()
        else:
            await cl.Message(
                content=(
                    "Please upload PDF documents using the file upload feature, or use "
                    "the button 'Lista PDF-uri din baza de date'."
                ),
                actions=[
                    cl.Action(
                        name="open_db_dropdown",
                        value="open",
                        description="Alege PDF din baza de date",
                        payload={"source": "empty_state"},
                    )
                ],
            ).send()


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

        if parse_result['success'] and parse_result['text']:
            # Save directly to output.txt (just the raw text)
            with open("output.txt", 'w', encoding='utf-8') as f:
                f.write(parse_result['text'])

            # Send success message
            msg = f"""✅ Parser Verification Complete!

File: {matching_pdf['name']}
Pages: {parse_result['page_count']}
Type: {'Scanned (OCR)' if parse_result['is_scanned'] else 'Regular Text'}

✅ output.txt created with {len(parse_result['text'])} characters"""

            await cl.Message(content=msg).send()
        else:
            await cl.Message(content=f"❌ Failed to parse PDF: {parse_result['error']}").send()

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

        if result['success']:
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
                msg = f"""📊 **Academic Audit Results**

**File:** {pdf_name}

**Status:** {status_icon} {status}

"""

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
                msg = f"""📊 **Validation Analysis**

**File:** {pdf_name}

**Raw Analysis:**
{result.get('raw_response', 'No response')}"""
                await cl.Message(content=msg).send()
        else:
            await cl.Message(content=f"❌ Analysis failed: {result.get('error', 'Unknown error')}").send()

    except Exception as e:
        print(f"ERROR in check_components_action: {str(e)}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Error: {str(e)}").send()
def get_loaded_pdfs() -> List[dict]:
    """Retrieve the currently loaded PDF documents."""
    return pdf_documents


def clear_pdfs():
    """Clear all loaded PDF documents."""
    global pdf_documents
    pdf_documents = []

