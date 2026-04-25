import streamlit as st
import os
import tempfile
import base64
import pymupdf4llm
from typing import List

# Import your existing backend modules
from gemini_backend import get_gemini_backend
from pdf_parser import get_pdf_parser
from queries import compare_fd_pi, save_documents_to_files, check_vague_content_and_bibliography
from pdf_generator import generate_pdf_from_text  # NEW IMPORT

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Academic PDF Auditor")


# --- Helper Functions ---
def display_pdf(file_bytes: bytes, file_name: str):
    st.download_button(
        label=f"💾 Open {file_name} externally (if viewer below is blank)",
        data=file_bytes,
        file_name=file_name,
        mime="application/pdf",
        key=f"dl_{file_name}"
    )

    try:
        base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
        pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf">'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception:
        st.warning("File is too large to render directly in the browser. Please use the download button above.")


def parse_uploaded_file(file, role: str) -> dict:
    parser = get_pdf_parser()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        file_bytes = file.read()
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    # Dacă suntem în modul EDIT_DOC, vrem structura Markdown (as_markdown=True)
    wants_markdown = (role == "EDIT_DOC")

    result = parser.parse_pdf(tmp_path, as_markdown=wants_markdown)
    os.unlink(tmp_path)

    if result and result.get("success"):
        return {
            "role": role,
            "name": file.name,
            "pages": result.get("page_count"),
            "full_text": result.get("text") or "",
            "is_scanned": result.get("is_scanned"),
            "extraction_method": result.get("method"),
            "bytes": file_bytes
        }
    else:
        st.error(f"Failed to parse {file.name}: {result.get('error')}")
        return None

# --- State Initialization ---
if 'audit_doc' not in st.session_state:
    st.session_state.audit_doc = None
if 'compare_docs' not in st.session_state:
    st.session_state.compare_docs = []
if 'audit_result' not in st.session_state:
    st.session_state.audit_result = None
if 'compare_result' not in st.session_state:
    st.session_state.compare_result = None
if 'competencies_result' not in st.session_state:
    st.session_state.competencies_result = None
if 'edit_doc' not in st.session_state:  # NEW for Mode 3
    st.session_state.edit_doc = None
if 'vague_doc' not in st.session_state:  # NEW for Mode 4
    st.session_state.vague_doc = None
if 'vague_result' not in st.session_state:  # NEW for Mode 4
    st.session_state.vague_result = None

# --- Sidebar Navigation ---
st.sidebar.title("🛠️ Instrumente")
app_mode = st.sidebar.radio("Alege un flux de lucru:", [
    "1. Audit Fișa Disciplinei (FD)",
    "2. Comparație FD vs PI",
    "3. Editare & regenerare PDF",
    "4. PI: Conținut vag & bibliografie neactualizată",
])

st.sidebar.divider()
st.sidebar.info(
    "Încarcă fișierele în zona principală pentru a începe. "
    "Schimbarea modului va modifica inputurile necesare."
)

# ==========================================
# MODE 1: SINGLE DOCUMENT AUDIT (Existing Code)
# ==========================================
if app_mode == "1. Audit Fișa Disciplinei (FD)":
    st.title("🔍 Audit Fișa Disciplinei (FD)")
    st.caption("Încarcă o Fișă a Disciplinei și rulează audit strict sau evaluarea competențelor.")

    uploaded_file = st.file_uploader("Încarcă Fișa Disciplinei (1 PDF)", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        if st.button("🔄 Parsează documentul", type="primary"):
            with st.spinner("Se parsează PDF-ul..."):
                doc = parse_uploaded_file(uploaded_file, "FD")
                if doc:
                    st.session_state.audit_doc = doc
                    st.session_state.audit_result = None
                    st.session_state.competencies_result = None
                    st.success("✅ Document parsat cu succes!")

    if st.session_state.audit_doc:
        doc = st.session_state.audit_doc
        st.divider()
        tab_doc, tab_tools, tab_results = st.tabs(["📄 Document", "🧰 Instrumente", "📊 Rezultate"])

        with tab_doc:
            c1, c2 = st.columns([0.55, 0.45])
            with c1:
                st.subheader(f"📄 {doc['name']}")
                st.caption(
                    f"Pagini: {doc.get('pages')} · Tip: {'Scanat (OCR)' if doc.get('is_scanned') else 'Text'} · "
                    f"Metodă: {doc.get('extraction_method')}"
                )
                display_pdf(doc['bytes'], doc['name'])
            with c2:
                with st.expander("📝 Text extras (preview)"):
                    text_preview = (doc.get('full_text') or "").strip()
                    if not text_preview:
                        st.warning("Nu s-a extras text.")
                    else:
                        st.text(text_preview[:5000] + ("..." if len(text_preview) > 5000 else ""))

        with tab_tools:
            st.subheader("📊 Unelte de analiză")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("▶️ Audit strict (structură + calcule)", use_container_width=True, type="primary"):
                    with st.spinner("Se analizează structura și calculele..."):
                        gemini = get_gemini_backend()
                        st.session_state.audit_result = gemini.check_missing_components(doc['full_text'], doc['name'])
                        st.session_state.competencies_result = None
            with b2:
                if st.button("🧠 Evaluare competențe (recomandări)", use_container_width=True):
                    with st.spinner("Se evaluează competențele..."):
                        gemini = get_gemini_backend()
                        st.session_state.competencies_result = gemini.analyze_and_recommend_competencies(
                            doc['full_text'], doc['name'])
                        st.session_state.audit_result = None

        with tab_results:
            if st.session_state.audit_result:
                st.markdown("### ✅ Rezultat audit strict")
                result = st.session_state.audit_result
                if result.get('success'):
                    st.json(result.get('analysis'))
                else:
                    st.error(result.get('error', 'Eroare la audit'))
            elif st.session_state.competencies_result:
                st.markdown("### ✅ Rezultat evaluare competențe")
                result = st.session_state.competencies_result
                if result.get('success'):
                    st.json(result.get('analysis'))
                else:
                    st.error(result.get('error', 'Eroare la evaluare'))
            else:
                st.info("Rulează o analiză din tab-ul **Instrumente** pentru a vedea rezultatele aici.")


# ==========================================
# MODE 2: DOCUMENT COMPARISON (Existing Code)
# ==========================================
elif app_mode == "2. Comparație FD vs PI":
    st.title("⚖️ Comparație FD vs PI")
    st.caption("Încarcă exact 2 PDF-uri (în ordine: FD apoi PI). Se vor salva în `fd.txt` și `pi.txt`.")

    uploaded_files = st.file_uploader(
        "Încarcă exact 2 PDF-uri (FD primul, PI al doilea)",
        type="pdf",
        accept_multiple_files=True,
    )

    if uploaded_files and len(uploaded_files) == 2:
        if st.button("🔄 Parsează ambele documente", type="primary"):
            with st.spinner("Se parsează PDF-urile..."):
                docs = [parse_uploaded_file(file, "FD" if idx == 0 else "PI") for idx, file in
                        enumerate(uploaded_files)]
                if all(docs):
                    st.session_state.compare_docs = docs
                    st.session_state.compare_result = None
                    save_documents_to_files(docs[0]["full_text"], docs[1]["full_text"], "fd.txt", "pi.txt")
                    st.success("✅ Ambele documente au fost parsate și salvate!")

    if len(st.session_state.compare_docs) == 2:
        st.divider()
        fd_doc, pi_doc = st.session_state.compare_docs[0], st.session_state.compare_docs[1]

        tab_rep, tab_view = st.tabs(["📊 Raport", "📄 PDF-uri"])

        with tab_rep:
            if st.button("▶️ Rulează comparația AI", use_container_width=True, type="primary"):
                with st.spinner("Se generează raportul de comparație..."):
                    st.session_state.compare_result = compare_fd_pi(fd_doc['full_text'], pi_doc['full_text'])

            if st.session_state.compare_result:
                result = st.session_state.compare_result
                if result.get('success'):
                    st.text_area("Raport", value=result.get('analysis') or "", height=450)
                else:
                    st.error(result.get('error', 'Comparația a eșuat'))
            else:
                st.info("Apasă **Rulează comparația AI** pentru a genera raportul.")

        with tab_view:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("FD")
                display_pdf(fd_doc['bytes'], fd_doc['name'])
            with col2:
                st.subheader("PI")
                display_pdf(pi_doc['bytes'], pi_doc['name'])


# ==========================================
# MODE 3: EDIT & REGENERATE PDF (NEW)
# ==========================================
elif app_mode == "3. Editare & regenerare PDF":
    st.title("✏️ Editare & regenerare PDF")
    st.caption("Încarcă un PDF, editează textul extras și generează un PDF nou.")

    uploaded_file = st.file_uploader("Încarcă PDF pentru editare", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        if st.button("🔄 Extrage text pentru editare", type="primary"):
            with st.spinner("Se extrage textul..."):
                doc = parse_uploaded_file(uploaded_file, "EDIT_DOC")
                if doc:
                    st.session_state.edit_doc = doc
                    st.success("✅ Text extras! Poți edita mai jos.")

    if st.session_state.edit_doc:
        st.divider()
        doc = st.session_state.edit_doc

        st.markdown(f"### Editare: {doc['name']}")

        # 1. Text Area for user to edit the text
        edited_text = st.text_area("Editează textul de mai jos:", value=doc['full_text'], height=500)

        # 2. Button to generate the new PDF
        if st.button("⚙️ Generează PDF nou din text", type="primary"):
            with st.spinner("Se construiește noul PDF..."):
                try:
                    new_pdf_bytes = generate_pdf_from_text(edited_text)

                    st.success("🎉 PDF-ul nou a fost generat cu succes!")

                    # Provide the download button for the new PDF
                    st.download_button(
                        label="⬇️ Descarcă PDF-ul modificat",
                        data=new_pdf_bytes,
                        file_name=f"modified_{doc['name']}",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")


# ==========================================
# MODE 4: PI - VAGUE CONTENT & OUTDATED BIBLIOGRAPHY (NEW)
# ==========================================
elif app_mode == "4. PI: Conținut vag & bibliografie neactualizată":
    st.title("⚠️ PI: Conținut vag & bibliografie neactualizată")
    st.caption(
        "Încarcă un Plan de Învățământ (PI). Vom parsa textul și vom genera un raport despre formulări vagi și bibliografie neactualizată."
    )

    uploaded_file = st.file_uploader("Încarcă Planul de Învățământ (1 PDF)", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        c1, c2 = st.columns([0.35, 0.65])
        with c1:
            if st.button("🔄 Parsează PI", type="primary", use_container_width=True):
                with st.spinner("Se parsează PI..."):
                    doc = parse_uploaded_file(uploaded_file, "PI")
                    if doc:
                        st.session_state.vague_doc = doc
                        st.session_state.vague_result = None
                        st.success("✅ PI parsat cu succes!")
        with c2:
            st.info("După parsare, apasă **Generează raport**.")

    if st.session_state.vague_doc:
        doc = st.session_state.vague_doc
        st.divider()

        tab_pi, tab_report = st.tabs(["📄 Document", "📋 Raport"])

        with tab_pi:
            a, b = st.columns([0.55, 0.45])
            with a:
                st.subheader(f"📄 {doc['name']}")
                st.caption(
                    f"Pagini: {doc.get('pages')} · Tip: {'Scanat (OCR)' if doc.get('is_scanned') else 'Text'} · "
                    f"Metodă: {doc.get('extraction_method')}"
                )
                display_pdf(doc['bytes'], doc['name'])
            with b:
                with st.expander("📝 Text extras (preview)"):
                    text_preview = (doc.get('full_text') or "").strip()
                    if not text_preview:
                        st.warning("Nu s-a extras text din document.")
                    else:
                        st.text(text_preview[:5000] + ("..." if len(text_preview) > 5000 else ""))

        with tab_report:
            st.subheader("📋 Raport: conținut vag & bibliografie")
            if st.button("▶️ Generează raport", type="primary", use_container_width=True):
                with st.spinner("Se generează raportul... (poate dura câteva secunde)"):
                    st.session_state.vague_result = check_vague_content_and_bibliography(
                        doc.get('full_text') or "",
                        doc.get('name') or "PI",
                    )

            if st.session_state.vague_result:
                res = st.session_state.vague_result
                if res.get('success'):
                    st.text_area("Raport", value=res.get('analysis') or "", height=550)
                else:
                    st.error(res.get('error', 'Analiza a eșuat'))
            else:
                st.info("Apasă **Generează raport** pentru a rula analiza.")
