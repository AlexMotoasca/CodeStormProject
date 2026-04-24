import chainlit as cl
import PyPDF2
from pathlib import Path
from typing import List
from gemini_backend import get_gemini_backend

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
    gemini = get_gemini_backend()

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

                    # Extract text from all pages
                    full_text = ""
                    for page in pdf_reader.pages:
                        full_text += page.extract_text() + "\n"

                    # Get preview from first page
                    first_page_text = pdf_reader.pages[0].extract_text()[:200]

                    pdf_documents.append({
                        'name': file.name,
                        'path': pdf_path,
                        'pages': num_pages,
                        'preview': first_page_text,
                        'full_text': full_text
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

            summary += "✨ Both documents are ready for processing!\n\n"
            summary += "You can now:\n"
            summary += "- Ask questions about the documents\n"
            summary += "- Request summaries\n"
            summary += "- Compare documents\n"
            summary += "- Extract specific information"

            await cl.Message(content=summary).send()

        elif len(pdf_documents) == 1:
            await cl.Message(
                content="ℹ️ 1 document uploaded. Please upload 1 more PDF document."
            ).send()
    else:
        # Handle text messages with Gemini
        if pdf_documents:
            user_input = message.content.strip().lower()

            # Summarize command
            if "summarize" in user_input or "summary" in user_input:
                await cl.Message(content="📝 Generating summary...").send()
                for i, pdf in enumerate(pdf_documents, 1):
                    summary = gemini.summarize_pdf(pdf['full_text'])
                    await cl.Message(
                        content=f"**Summary of {pdf['name']}:**\n\n{summary}"
                    ).send()

            # Compare documents
            elif "compare" in user_input and len(pdf_documents) == 2:
                await cl.Message(content="🔍 Comparing documents...").send()
                comparison = gemini.compare_pdfs(
                    pdf_documents[0]['full_text'],
                    pdf_documents[1]['full_text']
                )
                await cl.Message(
                    content=f"**Comparison Result:**\n\n{comparison}"
                ).send()

            # General questions
            else:
                await cl.Message(content="🤔 Analyzing documents...").send()

                # Combine PDFs for analysis
                combined_text = "\n\n---\n\n".join([
                    f"Document: {pdf['name']}\n{pdf['full_text']}"
                    for pdf in pdf_documents
                ])

                analysis = gemini.analyze_pdf_content(combined_text, message.content)
                await cl.Message(
                    content=f"**Analysis:**\n\n{analysis}"
                ).send()
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

