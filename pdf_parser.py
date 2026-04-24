# importing required modules
from pypdf import PdfReader

# creating a pdf reader object
reader = PdfReader('PDFs/fisa_disciplina.pdf')

# printing number of pages in pdf file
print(len(reader.pages))

# getting a specific page from the pdf file
page = reader.pages[0]

# extracting text from page
text = page.extract_text()

# printing text
print(text)

# writing text to a .txt file
with open("output.txt", "w", encoding="utf-8") as file:
    file.write(text)