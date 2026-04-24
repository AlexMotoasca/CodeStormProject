"""
Gemini API Backend Module

This module handles all interactions with Google's Gemini 1.5 Flash API.
"""

import os
import json
from typing import Optional, List
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
        Generate text using Gemini API.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating text: {str(e)}"

    def analyze_pdf_content(self, pdf_text: str, query: str) -> str:
        """
        n or analysis request

        Returns:
            Analysis result
        """
        prompt = f"""Please analyze the following PDF content and answer the query.

PDF Content:
{pdf_text}

Query: {query}

Please provide a comprehensive and clear response."""

        return self.generate_text(prompt)

    def summarize_pdf(self, pdf_text: str) -> str:
        """
        Summarize PDF content using Gemini.

        Args:
            pdf_text: The extracted text from PDF

        Returns:
            Summary of the PDF
        """
        prompt = f"""Please provide a concise summary of the following PDF content:

{pdf_text}

Provide a clear, structured summary highlighting the key points."""

        return self.generate_text(prompt)

    def compare_pdfs(self, pdf1_text: str, pdf2_text: str, query: Optional[str] = None) -> str:
        """
        Compare two PDF documents.

        Args:
            pdf1_text: Text from first PDF
            pdf2_text: Text from second PDF
            query: Optional specific comparison query

        Returns:
            Comparison analysis
        """
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
        """
        Extract specific information from PDF.

        Args:
            pdf_text: The extracted text from PDF
            info_type: Type of information to extract (e.g., 'dates', 'names', 'amounts')

        Returns:
            Extracted information
        """
        prompt = f"""Extract all {info_type} from the following PDF content:

{pdf_text}

Please list them in a structured format."""

        return self.generate_text(prompt)

    def start_chat_session(self):
        """Start a multi-turn chat session."""
        self.chat_history = []
        self.chat = self.model.start_chat(history=self.chat_history)

    def send_chat_message(self, message: str) -> str:
        """
        Send a message in the chat session.

        Args:
            message: The message to send

        Returns:
            Chat response
        """
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
        Check if the PDF has any missing or incomplete components using strict academic audit.
        Optimized for free tier API quota.

        Args:
            pdf_text: The extracted text from PDF
            pdf_name: The name of the PDF file

        Returns:
            Dictionary with analysis results in JSON format
        """
        # Optimized prompt - concise but complete validation rules
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

            # Try to parse the JSON response
            try:
                import json
                analysis_json = json.loads(result)
                return {
                    "success": True,
                    "analysis": analysis_json,
                    "raw_response": result
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw response
                return {
                    "success": True,
                    "analysis": None,
                    "raw_response": result,
                    "note": "Response could not be parsed as JSON. See raw_response."
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }


# Global instance
gemini_backend = GeminiBackend()


def get_gemini_backend() -> GeminiBackend:
    """Get the global Gemini backend instance."""
    return gemini_backend

