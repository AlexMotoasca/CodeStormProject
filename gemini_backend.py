"""
Gemini API Backend Module

This module handles all interactions with Google's Gemini 1.5 Flash API.
"""

import os
import json
import time
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# Use Gemini 2.5 Flash model (available and fast)
MODEL_NAME = "gemini-2.5-flash"


class GeminiBackend:
    """Backend class for Gemini API interactions."""

    def __init__(self):
        """Initialize the Gemini backend."""
        self.model = genai.GenerativeModel(MODEL_NAME)
        self.chat_history = []

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Gemini API with automatic Rate Limit handling.
        """
        max_retries = 3
        wait_time = 25 # Wait 25 seconds if we hit a 429 Quota error

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                # Catch the 429 Quota limit specifically
                if "429" in error_str and attempt < max_retries - 1:
                    print(f"⚠️ API Rate limit hit! Pausing for {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue # Try again after sleeping

                return f"Error generating text: {error_str}"

    def analyze_pdf_content(self, pdf_text: str, query: str) -> str:
        prompt = f"""Please analyze the following PDF content and answer the query.
PDF Content:\n{pdf_text}\n\nQuery: {query}\n\nPlease provide a comprehensive and clear response."""
        return self.generate_text(prompt)

    def summarize_pdf(self, pdf_text: str) -> str:
        prompt = f"""Please provide a concise summary of the following PDF content:\n{pdf_text}\nProvide a clear, structured summary highlighting the key points."""
        return self.generate_text(prompt)

    def compare_pdfs(self, pdf1_text: str, pdf2_text: str, query: Optional[str] = None) -> str:
        if query:
            prompt = f"Compare these two PDF documents with focus on: {query}\n\nDocument 1:\n{pdf1_text}\n\nDocument 2:\n{pdf2_text}\n\nPlease provide a detailed comparison."
        else:
            prompt = f"Compare these two PDF documents and highlight their differences and similarities:\n\nDocument 1:\n{pdf1_text}\n\nDocument 2:\n{pdf2_text}\n\nPlease provide a detailed comparison."
        return self.generate_text(prompt)

    def extract_key_information(self, pdf_text: str, info_type: str) -> str:
        prompt = f"Extract all {info_type} from the following PDF content:\n{pdf_text}\n\nPlease list them in a structured format."
        return self.generate_text(prompt)

    def start_chat_session(self):
        self.chat_history = []
        self.chat = self.model.start_chat(history=self.chat_history)

    def send_chat_message(self, message: str) -> str:
        try:
            if not hasattr(self, 'chat'):
                self.start_chat_session()
            response = self.chat.send_message(message)
            return response.text
        except Exception as e:
            return f"Error in chat: {str(e)}"

    def reset_chat(self):
        self.chat_history = []
        if hasattr(self, 'chat'):
            delattr(self, 'chat')

    def check_missing_components(self, pdf_text: str, pdf_name: str) -> dict:
        master_prompt = f"""Auditor academic. Validează "Fișa Disciplinei" și returnează JSON:

VALIDĂRI MATEMATICE - verifică acestea:
1. Ore/săptămână = Curs + Seminar/Lab
2. Ore total sem = Curs + Seminar/Lab  
3. Ore total = Ore/săpt × 14
4. Ore individuale = Suma (Manual + Doc + Prep + Tutoriat + Exam + Altele)
5. Total sem = Ore sem + Ore individ
6. Credite = Total sem / 25 (max 30 ECTS)
7. Ore Curs (tabel 8.1) = Curs (sec 3.5)
8. Ore Seminar (tabel 8.2) = Seminar (sec 3.6)
9. Pondere eval = 100%

STRUCTURĂ OBLIGATORIE:
- Date program (Instituție, Facultate, Program)
- Date disciplină (Denumire, Titulari, An, Semestru)
- Timp estimat (3.1-3.9)
- Precondiții, Condiții (5.1, 5.2)
- Competențe (Prof + Transversale)
- Obiective (7.1, 7.2)
- Conținuturi (8.1 Curs, 8.2 Seminar, Bibliografie)
- Evaluare (Criterii, metode, pondere, standard minim)
- Semnături finale

Returnează DOAR valid JSON:
{{
  "status": "VALID|INVALID",
  "math_errors": [{{"rule": "...", "expected": "...", "found": "...", "details": "..."}}],
  "structural_errors": [{{"section": "...", "issue": "...", "details": "..."}}],
  "missing_components": ["..."],
  "general_warnings": ["..."]
}}

PDF: {pdf_name}
TEXT: {pdf_text[:4000]}

JSON doar:"""

        try:
            result = self.generate_text(master_prompt)
            try:
                analysis_json = json.loads(result)
                return {"success": True, "analysis": analysis_json, "raw_response": result}
            except json.JSONDecodeError:
                return {"success": True, "analysis": None, "raw_response": result, "note": "Response could not be parsed as JSON."}
        except Exception as e:
            return {"success": False, "error": str(e), "analysis": None}

    def analyze_and_recommend_competencies(self, pdf_text: str, pdf_name: str) -> dict:
        """
        Analyzes the competencies in a Fișa Disciplinei and recommends improvements.
        Returns the result in JSON format.
        """
        master_prompt = f"""Ești un expert în design curricular universitar.
Sarcina ta este să analizezi "Fișa Disciplinei" de mai jos și să evaluezi competențele profesionale și transversale declarate, apoi să faci recomandări.

CERINȚE DE BAZĂ PENTRU ANALIZĂ:
1. Identifică numele disciplinei/materiei.
2. Extrage competențele profesionale și transversale actuale (sau constată lipsa lor).
3. Evaluează relevanța: Sunt aceste competențe potrivite pentru numele și conținutul materiei?
4. Formulază recomandări: Propune 2-3 competențe profesionale NOI sau îmbunătățite și 1-2 competențe transversale care s-ar potrivi mai bine cu materia, folosind verbe de acțiune clare (ex: a proiecta, a analiza, a implementa).

Returnează DOAR un obiect JSON valid, respectând strict această structură:
{{
  "nume_materie": "...",
  "competente_actuale_extrase": [
    "..."
  ],
  "evaluare_relevanta": "Scurtă analiză a competențelor actuale (1-2 propoziții)...",
  "recomandari_profesionale": [
    "Recomandare 1",
    "Recomandare 2"
  ],
  "recomandari_transversale": [
    "Recomandare 1"
  ]
}}

PDF: {pdf_name}
TEXT: {pdf_text[:5000]}

JSON doar:"""

        try:
            result = self.generate_text(master_prompt)
            # Try to parse the JSON response
            try:
                # Clean up potential markdown formatting from the response
                cleaned_result = result.strip()
                if cleaned_result.startswith('```json'):
                    cleaned_result = cleaned_result[7:]
                if cleaned_result.endswith('```'):
                    cleaned_result = cleaned_result[:-3]

                analysis_json = json.loads(cleaned_result.strip())
                return {"success": True, "analysis": analysis_json, "raw_response": result}
            except json.JSONDecodeError:
                return {"success": True, "analysis": None, "raw_response": result,
                        "note": "Response could not be parsed as JSON."}
        except Exception as e:
            return {"success": False, "error": str(e), "analysis": None}

    def check_vague_content_and_bibliography(self, pdf_text: str, pdf_name: str) -> dict:
        """
        Check for vague content and outdated bibliography in a Planul de Învățământ (PI).
        Returns analysis in formatted text (not JSON).
        """
        master_prompt = f"""Ești un expert în calitatea curriculumului și bibliografie academică.
Analizează "Planul de Învățământ" (PI) de mai jos și identifică:

1. CONȚINUT VAG:
   - Descrieri prea generale sau nespecifice ale obiectivelor
   - Competențe formulate vag sau imprecis
   - Descrieri de conținut care nu sunt concrete
   - Metodologii de predare neclare
   - Criterii de evaluare ambigue
   
2. BIBLIOGRAFIE NEACTUALIZATĂ:
   - Referințe mai vechi de 10 ani (cu excepția clasicilor consacrați)
   - Lipsă de surse recente (ultimii 3-5 ani)
   - Bibliografie incompletă (mai puțin de 5 surse pentru o disciplină)
   - Lipsă de resurse digitale/online
   - Lipsă de literatură actuală în domeniu

FORMAT RĂSPUNS - Scrie un raport CLAR ȘI CITIBIL:

📋 RAPORT ANALIZĂ - CONȚINUT VAG ȘI BIBLIOGRAFIE
==================================================

📄 Document analizat: {pdf_name}

---

❌ CONȚINUT VAG IDENTIFICAT:
• Pentru fiecare problemă găsită, scrie:
  - Locație în document (secțiune/cuvinte cheie)
  - Descrierea problemei
  - De ce este problematic
  - Sugestie de îmbunătățire

---

📚 BIBLIOGRAFIE - STATUS:
• Total surse identificate: [X]
• Surse din ultimii 5 ani: [Y]
• Surse mai vechi de 10 ani: [Z]
• Resurse digitale: [W]

---

⚠️ PROBLEME DE BIBLIOGRAFIE:
• Lipsuri și recomandări specifice
• Domenii care necesită referințe mai noi
• Tipuri de surse care lipsesc

---

RAPORT DETALIAT:

PI TEXT: {pdf_text[:6000]}

Scrie raportul în format text clar, ușor de citit. NU FOLOSI JSON."""

        try:
            result = self.generate_text(master_prompt)
            return {"success": True, "analysis": result}
        except Exception as e:
            return {"success": False, "error": str(e), "analysis": None}

    def generate_fd_skeleton_from_pi(self, pi_text: str, pi_name: str) -> dict:
        """Generate a Fișa Disciplinei (FD) skeleton pre-filled from a Plan de Învățământ (PI).

        Output must be Markdown-like text compatible with `pdf_generator.generate_pdf_from_text`:
        - Headings should start with # / ##
        - Tables must use |...| rows
        - Use placeholders (ex: "___") when PI doesn't contain a value.
        """

        # Optional: use an extracted FD as a style guide (kept short to avoid token blow-up)
        fd_style_guide = ""
        try:
            # `output.txt` exists in your repo and is a good example of FD structure
            with open("output.txt", "r", encoding="utf-8") as f:
                fd_style_guide = f.read(3500)
        except Exception:
            fd_style_guide = ""

        pi_excerpt = (pi_text or "").strip()
        # Keep within safe prompt limits
        pi_excerpt = pi_excerpt[:12000]

        master_prompt = f"""Ești un asistent academic specializat în redactarea documentului românesc „Fișa Disciplinei”.

SARCINĂ:
Primești textul extras dintr-un „Plan de Învățământ (PI)”. Generează un **schelet complet** de „Fișa Disciplinei (FD)”,
pre-completat cu informațiile pe care le poți deduce din PI.

REGULI CRITICE:
1) Returnează DOAR text (NU JSON, NU explicații, NU markdown code fences).
2) Păstrează structura tipică FD: secțiunile 1-10 + semnături.
3) Folosește tabele cu separator „|” (ca în exemplu). Dacă o valoare lipsește, pune „___”.
4) Nu inventa date (nume cadre didactice, ore, credite) dacă nu sunt în PI. Mai bine „___”.
5) Scrie în limba română, cu diacritice.

FORMAT:
- Folosește titluri cu „##” pentru secțiuni.
- În secțiunea 8. Conținuturi, include tabelele 8.1 Curs și 8.2 Seminar/lab/proiect (chiar dacă rămân goale/placeholder).

STIL EXEMPLU (doar ca ghid de format, nu copia conținutul):
{fd_style_guide}

DOCUMENT SURSĂ:
PI (nume fișier): {pi_name}

TEXT PI:
{pi_excerpt}

Acum generează „Fișa Disciplinei” (FD) completă ca schelet."""

        try:
            result = self.generate_text(master_prompt)
            cleaned = (result or "").strip()
            # Remove accidental fences if the model adds them
            if cleaned.startswith("```"):
                cleaned = cleaned.lstrip("`")
            if cleaned.endswith("```"):
                cleaned = cleaned.rstrip("`")
            cleaned = cleaned.strip()

            if not cleaned or cleaned.lower().startswith("error generating text:"):
                return {"success": False, "error": cleaned or "Empty response", "fd_text": None}

            return {"success": True, "fd_text": cleaned}
        except Exception as e:
            return {"success": False, "error": str(e), "fd_text": None}


# Global instance
gemini_backend = GeminiBackend()

def get_gemini_backend() -> GeminiBackend:
    return gemini_backend