"""Gemini AI Service - Wrapper for Google's Gemini API."""
import os
import json
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"


class GeminiService:
    """Service for Gemini API interactions."""

    def __init__(self):
        """Initialize the Gemini service."""
        self.model = genai.GenerativeModel(MODEL_NAME)
        self.chat_history = []

    def generate_text(self, prompt: str) -> str:
        """Generate text using Gemini API."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating text: {str(e)}"

    def analyze_pdf_content(self, pdf_text: str, query: str) -> str:
        """Analyze PDF content with a query."""
        prompt = f"""Please analyze the following PDF content and answer the query.

PDF Content:
{pdf_text}

Query: {query}

Please provide a comprehensive and clear response."""
        return self.generate_text(prompt)

    def summarize_pdf(self, pdf_text: str) -> str:
        """Summarize PDF content using Gemini."""
        prompt = f"""Please provide a concise summary of the following PDF content:

{pdf_text}

Provide a clear, structured summary highlighting the key points."""
        return self.generate_text(prompt)

    def compare_pdfs(self, pdf1_text: str, pdf2_text: str, query: Optional[str] = None) -> str:
        """Compare two PDF documents."""
        if query:
            prompt = f"""Compare these two PDF documents with focus on: {query}

Document 1:
{pdf1_text}

Document 2:
{pdf2_text}

Please provide a detailed comparison."""
        else:
            prompt = f"""Compare these two PDF documents and highlight their differences and similarities:

Document 1:
{pdf1_text}

Document 2:
{pdf2_text}

Please provide a detailed comparison."""
        return self.generate_text(prompt)

    def extract_key_information(self, pdf_text: str, info_type: str) -> str:
        """Extract specific information from PDF."""
        prompt = f"""Extract all {info_type} from the following PDF content:

{pdf_text}

Please list them in a structured format."""
        return self.generate_text(prompt)

    def start_chat_session(self):
        """Start a multi-turn chat session."""
        self.chat_history = []
        self.chat = self.model.start_chat(history=self.chat_history)

    def send_chat_message(self, message: str) -> str:
        """Send a message in the chat session."""
        try:
            if not hasattr(self, 'chat'):
                self.start_chat_session()
            response = self.chat.send_message(message)
            return response.text
        except Exception as e:
            return f"Error in chat: {str(e)}"

    def reset_chat(self):
        """Reset the chat history."""
        self.chat_history = []
        if hasattr(self, 'chat'):
            delattr(self, 'chat')

    def check_missing_components(self, pdf_text: str, pdf_name: str) -> dict:
        """
        Check if the PDF has any missing or incomplete components.
        Academic audit for Fișa Disciplinei.
        """
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
                return {
                    "success": True,
                    "analysis": analysis_json,
                    "raw_response": result
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "analysis": None,
                    "raw_response": result,
                    "note": "Response could not be parsed as JSON."
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }


# Global instance
gemini_service = GeminiService()


def get_gemini_service() -> GeminiService:
    """Get the Gemini service instance."""
    return gemini_service

