import psycopg2
import os


def incarca_toate_pdfurile(folder_sursa):
    try:
        # 1. Conectare la baza de date
        conn = psycopg2.connect(
            database="codestorm",
            user="postgres",
            password="1234",  # Pune parola setată de tine
            host="127.0.0.1",
            port="5432"
        )
        cursor = conn.cursor()

        # 2. Parcurgem folderul cu PDF-uri
        count = 0
        for fisier in os.listdir(folder_sursa):
            if fisier.endswith(".pdf"):
                cale_completa = os.path.join(folder_sursa, fisier)

                # Citim fișierul ca date binare
                with open(cale_completa, 'rb') as f:
                    blob_data = f.read()

                # 3. Inserăm în tabel
                sql = "INSERT INTO documente_scoala (nume_fisier, fisier_pdf) VALUES (%s, %s)"
                cursor.execute(sql, (fisier, psycopg2.Binary(blob_data)))
                count += 1
                print(f"Am încărcat: {fisier}")

        conn.commit()
        print(f"\nGata! Total fișiere încărcate: {count}")

    except Exception as e:
        print(f"Eroare: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()


# Rulează funcția (asigură-te că folderul 'documente' există)
# incarca_toate_pdfurile("PDFs")
