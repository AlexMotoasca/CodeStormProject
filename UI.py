import chainlit as cl
import PyPDF2
from pathlib import Path
from typing import List
from gemini_backend import get_gemini_backend
from pdf_parser import get_pdf_parser
import os

# Store uploaded PDFs in session
pdf_documents = []


@cl.on_chat_start
async def start():
    """Initialize the chat session and display the PDF import interface."""
    await cl.Message(
        content="Welcome! Please upload 1-2 PDF documents to get started. "
                "Use the file upload button below to select your PDF files.\n\n"
                "Features:\n"
                "✅ Auto-detect regular and scanned PDFs\n"
                "✅ Parse and extract text\n"
                "✅ Create output.txt with parsed content\n"
                "✅ AI-powered analysis with Gemini",
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming messages and process uploaded files."""
    global pdf_documents
    gemini = get_gemini_backend()
    parser = get_pdf_parser()

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
                pdf_path = file.path

                # Use enhanced parser to extract text (handles both regular and scanned PDFs)
                parse_result = parser.parse_pdf(pdf_path)

                if not parse_result['success']:
                    error_msg = parse_result['error'] if parse_result['error'] else "Unknown error occurred"
                    await cl.Message(
                        content=f"❌ Error processing {file.name}: {error_msg}"
                    ).send()
                    continue

                # Determine if scanned
                is_scanned = parse_result['is_scanned']
                method = parse_result['method']

                pdf_documents.append({
                    'name': file.name,
                    'path': pdf_path,
                    'pages': parse_result['page_count'],
                    'preview': parse_result['text'][:200] if parse_result['text'] else "",
                    'full_text': parse_result['text'],
                    'is_scanned': is_scanned,
                    'extraction_method': method
                })

                # Confirm upload with extraction method
                method_text = "🖼️ Scanned (OCR)" if is_scanned else "📄 Regular Text"
                await cl.Message(
                    content=f"✅ Successfully imported: **{file.name}**\n"
                            f"- Pages: {parse_result['page_count']}\n"
                            f"- Type: {method_text}\n"
                            f"- Preview: {parse_result['text'][:150]}..."
                ).send()

                # Add button to verify parser functionality and create output.txt
                verify_action = cl.Action(
                    name="verify_parser",
                    value=file.name,
                    payload={"pdf_name": file.name}
                )
                await cl.Message(
                    content=f"🔍 **Parser Verification**\n\n"
                            f"Click the button below to:\n"
                            f"✅ Verify parser functionality\n"
                            f"✅ Create output.txt with parsed text\n\n"
                            f"**PDF:** {file.name}",
                    actions=[verify_action]
                ).send()

            except Exception as e:
                await cl.Message(
                    content=f"❌ Error processing {file.name}: {str(e)}"
                ).send()

        # If 2 PDFs are uploaded, show summary
        if len(pdf_documents) == 2:
            summary = "📊 **PDF Summary**\n\n"
            for i, pdf in enumerate(pdf_documents, 1):
                doc_type = "🖼️ Scanned" if pdf['is_scanned'] else "📄 Regular"
                summary += f"**Document {i}: {pdf['name']}**\n"
                summary += f"- Pages: {pdf['pages']}\n"
                summary += f"- Type: {doc_type}\n"
                summary += f"- Extraction: {pdf['extraction_method']}\n\n"

            summary += "✨ Both documents are ready for processing!\n\n"
            summary += "You can now:\n"
            summary += "- Ask questions about the documents\n"
            summary += "- Request summaries\n"
            summary += "- Compare documents\n"
            summary += "- Extract specific information"

            await cl.Message(content=summary).send()

        elif len(pdf_documents) == 1:
            await cl.Message(
                content="ℹ️ 1 document uploaded. You can upload 1 more PDF document or continue with analysis."
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


@cl.action_callback("verify_parser")
async def verify_parser_action(action: cl.Action):
    """Handle parser verification button click."""
    parser = get_pdf_parser()

    # Get pdf_name from action payload
    pdf_name = action.payload.get("pdf_name")

    # Find the matching PDF in pdf_documents
    matching_pdf = next((pdf for pdf in pdf_documents if pdf['name'] == pdf_name), None)

    if not matching_pdf:
        await cl.Message(content=f"❌ Could not find PDF: {pdf_name}").send()
        return

    try:
        # Parse the PDF again to verify
        parse_result = parser.parse_pdf(matching_pdf['path'])

        if parse_result['success']:
            # Create output.txt with the parsed text
            output_file = "output.txt"

            # Create content for output file
            output_content = f"""=== PDF PARSER VERIFICATION REPORT ===

File: {matching_pdf['name']}
Pages: {parse_result['page_count']}
Type: {'Scanned (OCR)' if parse_result['is_scanned'] else 'Regular Text'}
Extraction Method: {parse_result['method']}
Timestamp: {__import__('datetime').datetime.now().isoformat()}

=== EXTRACTED TEXT ===

{parse_result['text']}

=== END OF DOCUMENT ===
"""

            # Save to output.txt
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)

            # Send verification report
            verification_msg = f"""✅ **PARSER VERIFICATION SUCCESSFUL**

📄 **File Details:**
- Name: {matching_pdf['name']}
- Pages: {parse_result['page_count']}
- PDF Type: {'🖼️ Scanned Document (OCR Used)' if parse_result['is_scanned'] else '📄 Regular Text PDF'}
- Extraction Method: {parse_result['method']}

📝 **Text Extraction:**
- Total Characters: {len(parse_result['text'])}
- Preview: {parse_result['text'][:200]}...

💾 **Output File:**
- ✅ Created: output.txt
- Location: {os.path.abspath(output_file)}
- Size: {len(output_content)} bytes

🎉 **Parser is working correctly!**
The parsed text has been saved to output.txt
"""

            await cl.Message(content=verification_msg).send()

        else:
            await cl.Message(
                content=f"❌ **PARSER VERIFICATION FAILED**\n\nError: {parse_result['error']}"
            ).send()

    except Exception as e:
        await cl.Message(
            content=f"❌ **VERIFICATION ERROR**\n\nException: {str(e)}"
        ).send()


def get_loaded_pdfs() -> List[dict]:
    """Retrieve the currently loaded PDF documents."""
    return pdf_documents


def clear_pdfs():
    """Clear all loaded PDF documents."""
    global pdf_documents
    pdf_documents = []

