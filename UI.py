import chainlit as cl
import PyPDF2
from pathlib import Path
from typing import List

# Store uploaded PDFs in session
pdf_documents = []


@cl.on_chat_start
async def start():
    """Initialize the chat session and display the PDF import interface."""
    await cl.Message(
        content="Welcome! Please upload 2 PDF documents to get started. "
                "Use the file upload button below to select your PDF files.",
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    global pdf_documents

    # Check if files were uploaded
    if message.elements:
        pdf_files = [file for file in message.elements if file.name.endswith('.pdf')]

        if not pdf_files:
            await cl.Message(
                content="❌ No PDF files found. Please upload PDF documents."
            ).send()
            return

        if len(pdf_files) > 2:
            await cl.Message(
                content="❌ Please upload maximum 2 PDF documents."
            ).send()
            return

        # Process uploaded PDFs
        pdf_documents = []
        for file in pdf_files:
            try:
                # Read PDF file
                pdf_path = file.path
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    num_pages = len(pdf_reader.pages)

                    # Extract text from first page as preview
                    first_page_text = pdf_reader.pages[0].extract_text()[:200]

                    pdf_documents.append({
                        'name': file.name,
                        'path': pdf_path,
                        'pages': num_pages,
                        'preview': first_page_text
                    })

                # Confirm upload
                await cl.Message(
                    content=f"✅ Successfully imported: **{file.name}**\n"
                            f"- Pages: {num_pages}\n"
                            f"- Preview: {first_page_text}..."
                ).send()

            except Exception as e:
                await cl.Message(
                    content=f"❌ Error processing {file.name}: {str(e)}"
                ).send()

        # If 2 PDFs are uploaded, show summary
        if len(pdf_documents) == 2:
            summary = "📊 **PDF Summary**\n\n"
            for i, pdf in enumerate(pdf_documents, 1):
                summary += f"**Document {i}: {pdf['name']}**\n"
                summary += f"- Pages: {pdf['pages']}\n\n"

            summary += "Both documents are ready for processing!"
            await cl.Message(content=summary).send()

        elif len(pdf_documents) == 1:
            await cl.Message(
                content="ℹ️ 1 document uploaded. Please upload 1 more PDF document."
            ).send()
    else:
        # Handle text messages
        if pdf_documents:
            response = f"I have {len(pdf_documents)} PDF document(s) loaded:\n"
            for pdf in pdf_documents:
                response += f"- {pdf['name']} ({pdf['pages']} pages)\n"
            await cl.Message(content=response).send()
        else:
            await cl.Message(
                content="Please upload PDF documents using the file upload feature."
            ).send()


def get_loaded_pdfs() -> List[dict]:
    """Retrieve the currently loaded PDF documents."""
    return pdf_documents


def clear_pdfs():
    """Clear all loaded PDF documents."""
    global pdf_documents
    pdf_documents = []

