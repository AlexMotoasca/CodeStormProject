import difflib
from pathlib import Path
from gemini_backend import GeminiBackend
    gemini_backend = GeminiBackend()

def analyse_pdf(pdf_txt):
    query = """Analizează textul de mai jos extras dintr-un PDF și validează calitatea datelor.

REGULI DE VALIDARE:
- Numele persoanelor nu trebuie să conțină cifre
- Locațiile nu trebuie să conțină cifre în afara numerelor de stradă
- Orice valoare numerică (vârstă, preț, cantitate, suprafață) trebuie să fie >= 0
- Datele calendaristice trebuie să fie valide și logice
- Adresele de email trebuie să respecte formatul standard
- Numerele de telefon trebuie să conțină doar cifre, spații, +, -, ()
- Câmpurile care par obligatorii nu trebuie să fie goale sau completate cu placeholder (ex: "N/A", "-", "???")
- Sumele financiare nu pot fi negative

Returnează un JSON cu structura:
{
  "document_type": "tipul documentului detectat",
  "total_issues": număr,
  "errors": [
    {
      "field": "numele câmpului",
      "value": "valoarea găsită",
      "rule_violated": "regula încălcată",
      "suggestion": "cum ar trebui să arate corect"
    }
  ],
  "warnings": [...același format...],
  "valid_fields": număr,
  "overall_status": "VALID" | "INVALID" | "NEEDS_REVIEW"
}"""
    result = gemini_backend.analyse_pdf(txt,query)
    return result

def compare_fd_pi(fd_txt,pi_txt):
    query = """Compară datele din cele două documente de mai jos și identifică toate inconsistențele dintre ele.

REGULI DE VERIFICARE A COERENȚEI:
- Datele de identificare (nume, CNP, serie buletin) trebuie să fie identice în ambele documente
- Vârsta / data nașterii trebuie să corespundă în ambele documente
- Anul de studiu / grupa / seria trebuie să fie același în ambele documente
- Adresa trebuie să fie aceeași sau modificarea să fie justificată
- Specializarea / facultatea / programul de studiu trebuie să coincidă
- Notele / mediile menționate trebuie să fie consistente
- Statusul (activ, exmatriculat, suspendat) trebuie să fie același
- Datele calendaristice (an înmatriculare, an absolvire) trebuie să fie logice și consistente
- Orice câmp care apare în ambele documente trebuie să aibă aceeași valoare sau o diferență explicabilă

IMPORTANT:
- O diferență este EROARE dacă valorile se contrazic fără explicație logică (ex: anul 2 vs anul 3)
- O diferență este AVERTISMENT dacă valorile sunt diferite dar ar putea fi justificate (ex: adresă schimbată)
- Ignoră diferențele de formatare (majuscule, spații, diacritice lipsă) dacă sensul e același

Returnează un JSON cu structura:
{{
  "document_1_type": "tipul primului document detectat",
  "document_2_type": "tipul celui de-al doilea document detectat",
  "total_inconsistencies": număr,
  "errors": [
    {{
      "field": "numele câmpului inconsistent",
      "value_doc1": "valoarea din documentul 1",
      "value_doc2": "valoarea din documentul 2",
      "explanation": "de ce e o problemă",
      "suggestion": "care valoare pare corectă sau cum se poate rezolva"
    }}
  ],
  "warnings": [
    {{
      "field": "numele câmpului",
      "value_doc1": "valoarea din documentul 1",
      "value_doc2": "valoarea din documentul 2",
      "explanation": "de ce e suspect dar nu neapărat greșit"
    }}
  ],
  "matching_fields": număr,
  "overall_status": "CONSISTENT" | "INCONSISTENT" | "NEEDS_REVIEW"
}}"""
    compare = gemini_backend.compare(fd_txt,pi_txt,query)
    return compare

def compare_fd(text1: str, text2: str) -> dict:
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    only_in_1 = []
    only_in_2 = []

    matcher = difflib.SequenceMatcher(None, lines1, lines2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            only_in_1.extend(lines1[i1:i2])
            only_in_2.extend(lines2[j1:j2])
        elif tag == "delete":
            only_in_1.extend(lines1[i1:i2])
        elif tag == "insert":
            only_in_2.extend(lines2[j1:j2])

    are_identical = not only_in_1 and not only_in_2

    return {
        "identical": are_identical,
        "differences_doc1": only_in_1,
        "differences_doc2": only_in_2,
    }