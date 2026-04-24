import streamlit as st
import os
import tempfile
import base64
import pymupdf4llm
from typing import List

# Import your existing backend modules
from gemini_backend import get_gemini_backend
from pdf_parser import get_pdf_parser
from queries import compare_fd_pi, save_documents_to_files
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

# --- Sidebar Navigation ---
st.sidebar.title("🛠️ Tools")
app_mode = st.sidebar.radio("Select a workflow:", [
    "1. Single Document Audit (FD)",
    "2. FD vs PI Comparison",
    "3. Edit & Regenerate PDF"  # NEW MODE
])

st.sidebar.divider()
st.sidebar.info("Upload files in the main window to begin. Switching modes will change the required inputs.")

# ==========================================
# MODE 1: SINGLE DOCUMENT AUDIT (Existing Code)
# ==========================================
if app_mode == "1. Single Document Audit (FD)":
    st.title("🔍 Single Document Audit")
    uploaded_file = st.file_uploader("Upload Fișa Disciplinei (1 PDF)", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        if st.button("🔄 Parse Document", type="primary"):
            with st.spinner("Parsing PDF..."):
                doc = parse_uploaded_file(uploaded_file, "FD")
                if doc:
                    st.session_state.audit_doc = doc
                    st.session_state.audit_result = None
                    st.session_state.competencies_result = None
                    st.success("✅ Document parsed successfully!")

    if st.session_state.audit_doc:
        doc = st.session_state.audit_doc
        st.divider()
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader(f"📄 Document: {doc['name']}")
            with st.expander("Show Extracted Text"):
                st.text(doc['full_text'][:2000] + "...")
            display_pdf(doc['bytes'], doc['name'])

        with col2:
            st.subheader("📊 Analysis Tools")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("▶️ Run Strict Audit", use_container_width=True):
                    with st.spinner("Analyzing structure and math..."):
                        gemini = get_gemini_backend()
                        st.session_state.audit_result = gemini.check_missing_components(doc['full_text'], doc['name'])
                        st.session_state.competencies_result = None
            with btn_col2:
                if st.button("🧠 Evaluate Competencies", use_container_width=True):
                    with st.spinner("Evaluating competencies..."):
                        gemini = get_gemini_backend()
                        st.session_state.competencies_result = gemini.analyze_and_recommend_competencies(
                            doc['full_text'], doc['name'])
                        st.session_state.audit_result = None

            st.divider()

            # (Afișarea rezultatelor pentru Audit și Competențe rămâne la fel ca înainte)
            if st.session_state.audit_result:
                st.markdown("### Academic Audit Results")
                result = st.session_state.audit_result
                if result.get('success'):
                    st.json(result.get('analysis'))  # Afișare rapidă JSON pentru brevitare în acest cod
                else:
                    st.error("Eroare la audit")
            elif st.session_state.competencies_result:
                st.markdown("### Competency Evaluation")
                result = st.session_state.competencies_result
                if result.get('success'):
                    st.json(result.get('analysis'))
                else:
                    st.error("Eroare la evaluare")


# ==========================================
# MODE 2: DOCUMENT COMPARISON (Existing Code)
# ==========================================
elif app_mode == "2. FD vs PI Comparison":
    st.title("⚖️ Document Comparison")
    uploaded_files = st.file_uploader("Upload exactly 2 PDFs (FD first, PI second)", type="pdf",
                                      accept_multiple_files=True)

    if uploaded_files and len(uploaded_files) == 2:
        if st.button("🔄 Parse Both Documents", type="primary"):
            with st.spinner("Parsing PDFs..."):
                docs = [parse_uploaded_file(file, "FD" if idx == 0 else "PI") for idx, file in
                        enumerate(uploaded_files)]
                if all(docs):
                    st.session_state.compare_docs = docs
                    st.session_state.compare_result = None
                    save_documents_to_files(docs[0]["full_text"], docs[1]["full_text"], "fd.txt", "pi.txt")
                    st.success("✅ Both documents parsed and saved!")

    if len(st.session_state.compare_docs) == 2:
        st.divider()
        fd_doc, pi_doc = st.session_state.compare_docs[0], st.session_state.compare_docs[1]

        if st.button("▶️ Run AI Comparison", use_container_width=True, type="primary"):
            with st.spinner("Generating comparison report..."):
                st.session_state.compare_result = compare_fd_pi(fd_doc['full_text'], pi_doc['full_text'])

        if st.session_state.compare_result:
            result = st.session_state.compare_result
            if result.get('success'):
                st.info(result.get('analysis'))

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            display_pdf(fd_doc['bytes'], fd_doc['name'])
        with col2:
            display_pdf(pi_doc['bytes'], pi_doc['name'])


# ==========================================
# MODE 3: EDIT & REGENERATE PDF (NEW)
# ==========================================
elif app_mode == "3. Edit & Regenerate PDF":
    st.title("✏️ Edit & Regenerate Document")
    st.markdown("Upload a PDF, edit the extracted text directly in the browser, and generate a new PDF file.")

    uploaded_file = st.file_uploader("Upload PDF to Edit", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        if st.button("🔄 Extract Text for Editing", type="primary"):
            with st.spinner("Extracting text..."):
                doc = parse_uploaded_file(uploaded_file, "EDIT_DOC")
                if doc:
                    st.session_state.edit_doc = doc
                    st.success("✅ Text extracted! You can now edit it below.")

    if st.session_state.edit_doc:
        st.divider()
        doc = st.session_state.edit_doc

        st.markdown(f"### Editing: {doc['name']}")

        # 1. Text Area for user to edit the text
        edited_text = st.text_area(
            "Modify the text below:",
            value=doc['full_text'],
            height=500
        )

        # 2. Button to generate the new PDF
        if st.button("⚙️ Generate New PDF from Text", type="primary"):
            with st.spinner("Building new PDF document..."):
                try:
                    new_pdf_bytes = generate_pdf_from_text(edited_text)

                    st.success("🎉 New PDF generated successfully!")

                    # Provide the download button for the new PDF
                    st.download_button(
                        label="⬇️ Download Modified PDF",
                        data=new_pdf_bytes,
                        file_name=f"modified_{doc['name']}",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")