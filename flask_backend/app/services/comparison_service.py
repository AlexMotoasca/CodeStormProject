"""Comparison Service - FD vs PI document comparison logic."""
import json
from typing import Dict, Any
from app.services.gemini_service import get_gemini_service


class ComparisonService:
    """Service for comparing FD and PI documents."""

    @staticmethod
    def compare_fd_pi(fd_text: str, pi_text: str) -> Dict[str, Any]:
        """
        Compare Fișa Disciplinei (FD) with Plan Învățământ (PI).
        
        Args:
            fd_text: Text from FD document
            pi_text: Text from PI document
            
        Returns:
            Structured comparison result
        """
        gemini = get_gemini_service()
        
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
{fd_text}

DOCUMENT 2 - Plan Învățământ:
{pi_text}

Scrie raportul în format text clar și ușor de citit. NU FOLOSI JSON."""

        try:
            response = gemini.compare_pdfs(fd_text, pi_text, query)
            
            return {
                'success': True,
                'analysis': response,
                'status': ComparisonService._extract_status(response)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'analysis': None
            }

    @staticmethod
    def _extract_status(response_text: str) -> str:
        """Extract comparison status from response text."""
        if 'CONSISTENT' in response_text.upper():
            return 'CONSISTENT'
        elif 'INCONSISTENT' in response_text.upper():
            return 'INCONSISTENT'
        else:
            return 'NEEDS_REVIEW'

    @staticmethod
    def compare_fd_simple(text1: str, text2: str) -> Dict[str, Any]:
        """
        Simple line-by-line comparison using difflib.
        
        Args:
            text1: First document text
            text2: Second document text
            
        Returns:
            Dictionary with differences
        """
        import difflib
        
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
            "success": True,
            "identical": are_identical,
            "differences_doc1": only_in_1,
            "differences_doc2": only_in_2,
        }


# Global instance
comparison_service = ComparisonService()


def get_comparison_service() -> ComparisonService:
    """Get the comparison service instance."""
    return comparison_service

