import difflib
import json
from pathlib import Path
from gemini_backend import get_gemini_backend

# Get the Gemini backend instance
gemini_backend = get_gemini_backend()


def compare_fd_pi(fd_txt, pi_txt):
    """
    Compare Fișa Disciplinei (FD) with Plan Învățământ (PI) documents.

    Args:
        fd_txt: Text from Fișa Disciplinei document
        pi_txt: Text from Plan Învățământ document

    Returns:
        Comparison analysis as formatted text
    """
    query = """Compară datele din cele două documente de mai jos și creează un raport detaliat cu toate inconsistențele.

REGULI DE VERIFICARE A COERENȚEI:
- Datele de identificare (program, facultate, departament) trebuie să fie identice
- Disciplinele / cursurile trebuie să coincidă
- Numărul de ore (curs, seminar, laborator) trebuie să fie consistent
- Creditele (ECTS) trebuie să se potrivească
- Anul de studiu / semestrul trebuie să fie același
- Competențele și obiectivele trebuie să fie în acord
- Evaluarea și ponderea notelor trebuie să fie coerente

FORMAT RĂSPUNS - Scrie un raport CLAR ȘI CITIBIL (NU JSON):

📊 RAPORT COMPARATIV FD vs PI
================================

🔍 STATUS GENERAL: [CONSISTENT / INCONSISTENT / NEEDS_REVIEW]

📋 STATISTICI:
- Câmpuri care se potrivesc: [X]
- Inconsistențe totale: [Y]

---

❌ ERORI CRITICE:
(pentru fiecare eroare: câmp, valoare în FD, valoare în PI, de ce e problemă, sugestie)

---

⚠️ AVERTISMENTE:
(pentru fiecare avertisment: câmp, valoare în FD, valoare în PI, de ce e suspect)

---

✅ CONCLUZII:
(rezumat final și recomandări)

DOCUMENT 1 - Fișa Disciplinei:
{fd_txt}

DOCUMENT 2 - Plan Învățământ:
{pi_txt}

Scrie raportul în format text clar și ușor de citit. NU FOLOSI JSON."""

    try:
        response = gemini_backend.compare_pdfs(fd_txt, pi_txt, query)

        return {
            "success": True,
            "analysis": response  # Return raw text directly
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis": None
        }


def compare_fd(text1: str, text2: str) -> dict:
    """
    Simple line-by-line comparison using difflib.

    Args:
        text1: First document text
        text2: Second document text

    Returns:
        Dictionary with differences
    """
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


def save_documents_to_files(fd_text: str, pi_text: str, fd_path: str = "fd.txt", pi_path: str = "pi.txt") -> dict:
    """
    Save parsed documents to separate text files.

    Args:
        fd_text: Fișa Disciplinei parsed text
        pi_text: Plan Învățământ parsed text
        fd_path: Path to save Fișa Disciplinei
        pi_path: Path to save Plan Învățământ

    Returns:
        Status dictionary
    """
    try:
        # Save Fișa Disciplinei
        with open(fd_path, 'w', encoding='utf-8') as f:
            f.write(fd_text)

        # Save Plan Învățământ
        with open(pi_path, 'w', encoding='utf-8') as f:
            f.write(pi_text)

        return {
            "success": True,
            "fd_file": fd_path,
            "pi_file": pi_path,
            "fd_size": len(fd_text),
            "pi_size": len(pi_text)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_vague_content_and_bibliography(pi_text: str, pi_name: str) -> dict:
    """
    Check for vague content and outdated bibliography in a Planul de Învățământ (PI).
    
    Args:
        pi_text: Text from Plan Învățământ document
        pi_name: Name of the PI document
    
    Returns:
        Analysis as formatted text (not JSON)
    """
    try:
        result = gemini_backend.check_vague_content_and_bibliography(pi_text, pi_name)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis": None
        }
