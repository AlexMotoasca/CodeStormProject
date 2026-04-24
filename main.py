"""
Main entry point for the PDF Import UI application using Chainlit.

Run this file with: chainlit run main.py
"""

import chainlit as cl
from UI import start as ui_start, handle_message


@cl.on_chat_start
async def start():
    """Initialize the chat session and display the PDF import interface."""
    await ui_start()


@cl.on_message
async def main_handler(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    await handle_message(message)


if __name__ == '__main__':
    print("Starting Chainlit UI...")
    print("Run: chainlit run main.py")
