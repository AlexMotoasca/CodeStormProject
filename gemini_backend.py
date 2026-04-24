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

# Use Gemini 1.5 Flash model
MODEL_NAME = "gemini-1.5-flash"


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
        Analyze PDF content using Gemini.

        Args:
            pdf_text: The extracted text from PDF
            query: The question or analysis request

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


# Global instance
gemini_backend = GeminiBackend()


def get_gemini_backend() -> GeminiBackend:
    """Get the global Gemini backend instance."""
    return gemini_backend

