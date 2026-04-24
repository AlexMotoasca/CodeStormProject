"""
Test the updated PDF parser on scanned PDFs
"""

from pdf_parser import get_pdf_parser

parser = get_pdf_parser()

print("=" * 60)
print("Testing PDF Parser on fisa_disciplina.pdf")
print("=" * 60)

result = parser.parse_pdf('PDFs/plan_invatamant.pdf')

print('\n=== RESULT ===')
print(f'Success: {result["success"]}')
print(f'Pages: {result["page_count"]}')
print(f'Is Scanned: {result["is_scanned"]}')
print(f'Method: {result["method"]}')
print(f'Error: {result["error"]}')

if result["text"]:
    print(f'\nText Preview ({len(result["text"])} chars):')
    print("---")
    print(result["text"][:500])
    print("---")

    # Save to file
    if parser.save_to_file(result["text"]):
        print("\n✅ Text saved to output.txt")
else:
    print('\n❌ No text extracted')

