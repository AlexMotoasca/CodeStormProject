"""
Main entry point for the PDF Import UI application using Chainlit.

Run this file with: chainlit run main.py
"""

import chainlit as cl
from UI import handle_message, get_loaded_pdfs, clear_pdfs


@cl.on_chat_start
async def start():
    """Initialize the chat session and display the PDF import interface."""
    await cl.Message(
        content="Welcome! Please upload 2 PDF documents to get started. "
                "Use the file upload button below to select your PDF files.",
    ).send()


@cl.on_message
async def main_handler(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    await handle_message(message)


if __name__ == '__main__':
    print("Starting Chainlit UI...")
    print("Run: chainlit run main.py")
