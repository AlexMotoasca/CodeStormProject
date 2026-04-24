# Standalone PDF Editor

Use `pdf_editor_standalone.py` if you want a separate UI without touching team files.

## What it does
- Lists files from `PDFs/`
- Loads and displays extracted text from a selected PDF
- Lets you edit the text
- Saves edited content as a new PDF in `edited_pdf/` (`<name>_edited.pdf`)
- Reuses original PDF text boxes to keep layout visually close to the source

## Run
```powershell
Set-Location "C:\Users\sebim\PycharmProjects\CodeStormProject"
python -m pip install -r requirements.txt
python pdf_editor_standalone.py
```

## Note
This does not overwrite original PDFs. It creates edited copies.
For very large rewrites, layout can still drift because PDF text objects are fixed boxes.

## Chainlit DB PDF flow
- In `main.py`, click `Lista PDF-uri din baza de date`
- Click `Vizualizeaza` to open a PDF from PostgreSQL directly in chat
- Click `Editeaza si salveaza`, then send edited text in the next message
- The app regenerates and saves the edited PDF back to DB, then shows it again inline

