import streamlit as st
import os
import tempfile
import base64


# Import your existing backend modules
from gemini_backend import get_gemini_backend
from pdf_parser import get_pdf_parser
from queries import (
    compare_fd_pi,
    save_documents_to_files,
    check_vague_content_and_bibliography,
    generate_fd_from_pi,
)
from pdf_generator import generate_pdf_from_text  # NEW IMPORT

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Academic PDF Auditor")


# --- UI Theme / CSS (User-friendly colors) ---
def _inject_css():
    st.markdown(
        """
        <style>
          /* Minimalist theme - neutral + one accent */
          :root {
            --cs-accent: #4f46e5;         /* indigo */
            --cs-border: rgba(148,163,184,0.35);
            --cs-muted: rgba(100,116,139,1);
            --cs-bg-soft: rgba(2,6,23,0.03);
          }

          /* Remove Streamlit chrome */
          #MainMenu { visibility: hidden; }
          footer { visibility: hidden; }
          header { visibility: hidden; }

          /* Layout */
          .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 1200px;
          }

          /* Header card (clean) */
          .cs-hero {
            background: var(--cs-bg-soft);
            border: 1px solid var(--cs-border);
            border-left: 4px solid var(--cs-accent);
            border-radius: 14px;
            padding: 14px 16px;
            margin: 0 0 14px 0;
          }
          .cs-hero-title { font-size: 1.22rem; font-weight: 800; margin: 0; }
          .cs-hero-sub { margin: 6px 0 0 0; color: var(--cs-muted); }
          .cs-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid var(--cs-border);
            background: rgba(255,255,255,0.7);
            color: rgba(30,41,59,1);
            margin-left: 10px;
            vertical-align: middle;
          }

          /* Buttons - minimalist */
          div.stButton > button {
            border-radius: 12px !important;
            border: 1px solid var(--cs-border) !important;
            padding: 0.55rem 0.9rem !important;
            font-weight: 700 !important;
            background: transparent !important;
          }
          div.stButton > button[kind="primary"] {
            background: var(--cs-accent) !important;
            border: 1px solid var(--cs-accent) !important;
            color: white !important;
          }

          /* Tabs */
          button[data-baseweb="tab"] {
            border-radius: 12px !important;
            padding: 8px 10px !important;
          }

          /* Inputs */
          [data-testid="stFileUploader"] {
            border: 1px dashed var(--cs-border);
            border-radius: 12px;
            padding: 10px;
          }

          /* Expander */
          details summary { font-weight: 700; }

          /* Sidebar */
          [data-testid="stSidebar"] {
            border-right: 1px solid var(--cs-border);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(mode_label: str):
    st.markdown(
        f"""
        <div class="cs-hero">
          <div>
            <span class="cs-hero-title">Academic PDF Auditor</span>
            <span class="cs-badge">{mode_label}</span>
          </div>
          <p class="cs-hero-sub">
            Încarcă PDF-urile, extrage textul și rulează audit / comparație / generare FD.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_inject_css()


# --- Helper Functions ---
def render_json_safely(result: dict, key_analysis: str = "analysis", key_raw: str = "raw_response"):
    """Render JSON-like results without crashing Streamlit.

    Streamlit's st.json expects a dict/list. If analysis is missing or not a dict/list,
    we fall back to showing raw text.
    """
    analysis = result.get(key_analysis)
    if isinstance(analysis, (dict, list)):
        st.json(analysis)
        return

    raw = result.get(key_raw) or analysis
    if raw is None:
        st.info("Nu există rezultat JSON de afișat.")
        return

    st.text_area("Răspuns (text brut)", value=str(raw), height=450)


def render_audit_report(analysis: dict):
    """Render a readable audit report from the JSON structure returned by check_missing_components."""
    status = (analysis.get("status") or "UNKNOWN").upper()
    status_icon = "✅" if status == "VALID" else ("❌" if status == "INVALID" else "ℹ️")

    math_errors = analysis.get("math_errors") or []
    structural_errors = analysis.get("structural_errors") or []
    missing_components = analysis.get("missing_components") or []
    warnings = analysis.get("general_warnings") or []

    st.markdown(
        f"""
**Status:** {status_icon} **{status}**  
**Erori matematice:** {len(math_errors)} · **Erori structurale:** {len(structural_errors)} · **Lipsuri:** {len(missing_components)}
"""
    )

    st.divider()
    st.markdown("#### 🧮 Erori matematice")
    if not math_errors:
        st.success("Nu au fost detectate erori matematice.")
    else:
        for i, err in enumerate(math_errors, 1):
            st.markdown(
                f"""**{i}. {err.get('rule','(regulă nedefinită)')}**  
- Așteptat: `{err.get('expected','N/A')}`  
- Găsit: `{err.get('found','N/A')}`  
- Detalii: {err.get('details','')}
"""
            )

    st.divider()
    st.markdown("#### 🧱 Probleme structurale")
    if not structural_errors:
        st.success("Structura documentului pare completă.")
    else:
        for i, err in enumerate(structural_errors, 1):
            st.markdown(
                f"""**{i}. {err.get('section','(secțiune nedefinită)')}**  
- Problemă: **{err.get('issue','N/A')}**  
- Detalii: {err.get('details','')}
"""
            )

    st.divider()
    st.markdown("#### 📌 Componente lipsă")
    if not missing_components:
        st.success("Nu par să lipsească componente obligatorii.")
    else:
        st.markdown("\n".join([f"- {c}" for c in missing_components]))

    if warnings:
        st.divider()
        st.markdown("#### ⚠️ Avertismente")
        st.markdown("\n".join([f"- {w}" for w in warnings]))


def render_competencies_report(analysis: dict):
    """Render a readable competencies report from the JSON structure."""
    st.markdown(f"**Materie:** {analysis.get('nume_materie','(necunoscut)')}")
    st.divider()

    st.markdown("#### 📥 Competențe extrase")
    extracted = analysis.get("competente_actuale_extrase") or []
    if extracted:
        st.markdown("\n".join([f"- {x}" for x in extracted]))
    else:
        st.info("Nu am putut extrage competențe clar definite din text.")

    st.divider()
    st.markdown("#### 🧠 Evaluare relevanță")
    st.write(analysis.get("evaluare_relevanta") or "")

    st.divider()
    st.markdown("#### ✅ Recomandări profesionale")
    prof = analysis.get("recomandari_profesionale") or []
    if prof:
        st.markdown("\n".join([f"- {x}" for x in prof]))
    else:
        st.info("Nu au fost generate recomandări profesionale.")

    st.divider()
    st.markdown("#### ✅ Recomandări transversale")
    trans = analysis.get("recomandari_transversale") or []
    if trans:
        st.markdown("\n".join([f"- {x}" for x in trans]))
    else:
        st.info("Nu au fost generate recomandări transversale.")


def display_pdf(file_bytes: bytes, file_name: str):
    st.download_button(
        label=f"💾 Descarcă / deschide {file_name} (dacă viewer-ul e gol)",
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


def parse_uploaded_file(file, role: str) -> dict | None:
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
if 'fdgen_doc' not in st.session_state:  # NEW for Mode 5
    st.session_state.fdgen_doc = None
if 'fdgen_text' not in st.session_state:  # NEW for Mode 5
    st.session_state.fdgen_text = None
if 'fdgen_pdf' not in st.session_state:  # NEW for Mode 5
    st.session_state.fdgen_pdf = None
if 'fdgen_pdf_path' not in st.session_state:  # NEW for Mode 5
    st.session_state.fdgen_pdf_path = None

# --- Sidebar Navigation ---
st.sidebar.title("🛠️ Instrumente")
app_mode = st.sidebar.radio("Alege un flux de lucru:", [
    "1. Audit Fișa Disciplinei (FD)",
    "2. Comparație FD vs PI",
    "3. Editare & regenerare PDF",
    "4. PI: Conținut vag & bibliografie neactualizată",
    "5. PI ➜ Generare automată schelet FD",
])

st.sidebar.divider()
st.sidebar.markdown("**Sfaturi rapide:**")
st.sidebar.markdown(
    "- Pentru comparație: încarcă **FD primul**, apoi **PI**.\n"
    "- Dacă download-ul PDF nu pornește, folosește calea *Fallback*."
)
st.sidebar.info(
    "Încarcă fișierele în zona principală pentru a începe. "
    "Schimbarea modului va modifica inputurile necesare."
)

# ==========================================
# MODE 1: SINGLE DOCUMENT AUDIT (Existing Code)
# ==========================================
if app_mode == "1. Audit Fișa Disciplinei (FD)":
    _render_hero("Audit FD")
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
                    analysis = result.get("analysis")
                    if isinstance(analysis, dict):
                        render_audit_report(analysis)
                        with st.expander("Detalii tehnice (JSON)"):
                            st.json(analysis)
                    else:
                        render_json_safely(result)
                else:
                    st.error(result.get('error', 'Eroare la audit'))
            elif st.session_state.competencies_result:
                st.markdown("### ✅ Rezultat evaluare competențe")
                result = st.session_state.competencies_result
                if result.get('success'):
                    analysis = result.get("analysis")
                    if isinstance(analysis, dict):
                        render_competencies_report(analysis)
                        with st.expander("Detalii tehnice (JSON)"):
                            st.json(analysis)
                    else:
                        render_json_safely(result)
                else:
                    st.error(result.get('error', 'Eroare la evaluare'))
            else:
                st.info("Rulează o analiză din tab-ul **Instrumente** pentru a vedea rezultatele aici.")


# ==========================================
# MODE 2: DOCUMENT COMPARISON (Existing Code)
# ==========================================
elif app_mode == "2. Comparație FD vs PI":
    _render_hero("Comparație")
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
    _render_hero("Editare PDF")
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
    _render_hero("PI: Vag & Bibliografie")
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


# ==========================================
# MODE 5: PI -> AUTO GENERATE FD SKELETON (NEW)
# ==========================================
elif app_mode == "5. PI ➜ Generare automată schelet FD":
    _render_hero("PI ➜ FD")
    st.title("🧩 PI ➜ Generare automată schelet Fișa Disciplinei")
    st.caption(
        "Flux: încarci PI → se extrage textul → Gemini generează schelet FD (pre-completat unde se poate) → îl poți edita → generezi PDF."
    )

    uploaded_file = st.file_uploader("Încarcă Planul de Învățământ (PI) (1 PDF)", type="pdf", accept_multiple_files=False)

    if uploaded_file:
        c1, c2, c3 = st.columns([0.28, 0.36, 0.36])
        with c1:
            if st.button("🔄 Parsează PI", type="primary", use_container_width=True):
                with st.spinner("Se parsează PI..."):
                    doc = parse_uploaded_file(uploaded_file, "PI")
                    if doc:
                        st.session_state.fdgen_doc = doc
                        st.session_state.fdgen_text = None
                        st.session_state.fdgen_pdf = None
                        st.session_state.fdgen_pdf_path = None
                        st.success("✅ PI parsat cu succes!")
        with c2:
            st.info("După parsare: apasă **Generează text FD**.")
        with c3:
            st.warning("Notă: dacă PI nu conține anumite câmpuri, ele vor apărea ca „___”.")

    if st.session_state.fdgen_doc:
        doc = st.session_state.fdgen_doc
        st.divider()

        tab_pi, tab_fd, tab_pdf = st.tabs(["📄 PI", "📝 Text FD", "📄 PDF generat"])

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
                with st.expander("📝 Text PI extras (preview)"):
                    pi_preview = (doc.get('full_text') or "").strip()
                    if not pi_preview:
                        st.warning("Nu s-a extras text din PI.")
                    else:
                        st.text(pi_preview[:5000] + ("..." if len(pi_preview) > 5000 else ""))

        with tab_fd:
            st.subheader("📝 Schelet Fișa Disciplinei (FD)")

            if st.button("✨ Generează text FD din PI", type="primary", use_container_width=True):
                with st.spinner("Se generează scheletul FD... (poate dura câteva secunde)"):
                    res = generate_fd_from_pi(doc.get('full_text') or "", doc.get('name') or "PI")
                    if res.get('success'):
                        st.session_state.fdgen_text = res.get('fd_text')
                        st.session_state.fdgen_pdf = None
                        out_path = res.get('out_path')
                        if out_path:
                            st.success(f"✅ Text FD generat și salvat în {out_path}.")
                        else:
                            st.success("✅ Text FD generat.")
                        if res.get('warning'):
                            st.warning(res.get('warning'))
                    else:
                        st.error(res.get('error', 'Generarea a eșuat'))

            if st.session_state.fdgen_text:
                st.caption("Poți edita textul înainte de generarea PDF-ului.")
                edited_fd_text = st.text_area(
                    "Text FD (editabil)",
                    value=st.session_state.fdgen_text,
                    height=520,
                )

                gen_col1, gen_col2 = st.columns([0.5, 0.5])
                with gen_col1:
                    if st.button("🧾 Generează PDF FD", type="primary", use_container_width=True):
                        with st.spinner("Se generează PDF-ul FD..."):
                            try:
                                pdf_bytes = generate_pdf_from_text(edited_fd_text)
                                st.session_state.fdgen_pdf = pdf_bytes
                                # keep updated text
                                st.session_state.fdgen_text = edited_fd_text

                                # Save PDF locally as a reliable fallback
                                try:
                                    out_pdf_path = os.path.abspath("FD_generat.pdf")
                                    with open(out_pdf_path, "wb") as f:
                                        f.write(pdf_bytes)
                                    st.session_state.fdgen_pdf_path = out_pdf_path
                                except Exception:
                                    st.session_state.fdgen_pdf_path = None

                                # also save locally
                                try:
                                    with open("fd_generated.txt", "w", encoding="utf-8") as f:
                                        f.write(edited_fd_text)
                                except Exception:
                                    pass

                                st.success("✅ PDF FD generat!")
                            except Exception as e:
                                st.error(f"Eroare la generarea PDF: {str(e)}")
                with gen_col2:
                    st.download_button(
                        label="⬇️ Descarcă text FD (fd_generated.txt)",
                        data=(edited_fd_text or "").encode("utf-8"),
                        file_name="fd_generated.txt",
                        mime="text/plain",
                        key="dl_fdgen_text",
                        use_container_width=True,
                    )
            else:
                st.info("Apasă **Generează text FD din PI** ca să obții scheletul.")

        with tab_pdf:
            st.subheader("📄 Fișa Disciplinei (FD) - PDF")
            if st.session_state.fdgen_pdf:
                pdf_bytes = st.session_state.fdgen_pdf

                # Download button with stable key (avoids widget key collisions on reruns)
                st.download_button(
                    label="⬇️ Descarcă PDF FD",
                    data=pdf_bytes,
                    file_name="FD_generat.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="dl_fdgen_pdf_primary",
                )

                # Show where we saved it on disk (fallback if browser download is blocked)
                if st.session_state.fdgen_pdf_path:
                    st.caption("Fallback: PDF-ul a fost salvat și local la:")
                    st.code(st.session_state.fdgen_pdf_path)

                display_pdf(pdf_bytes, "FD_generat.pdf")
            else:
                st.info("Generează PDF-ul din tab-ul **Text FD**.")

