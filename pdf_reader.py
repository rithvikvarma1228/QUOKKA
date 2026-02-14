import os
import re
from pypdf import PdfReader

DATA_PATH = "data"

def clean_text(text):
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove reference numbers like [1], [23]
    text = re.sub(r'\[[0-9]+\]', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Remove long sequences of non-word characters
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)

    return text.strip()


def extract_text_from_pdfs():
    all_text = ""

    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DATA_PATH, filename)
            reader = PdfReader(filepath)

            print(f"Reading {filename}...")

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    cleaned = clean_text(text)
                    all_text += cleaned + "\n"

    return all_text


if __name__ == "__main__":
    text = extract_text_from_pdfs()
    print("Extraction completed.")
    print("Total characters extracted:", len(text))
