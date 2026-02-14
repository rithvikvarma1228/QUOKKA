from pdf_reader import extract_text_from_pdfs
import re

def chunk_text(text, chunk_size=1000, overlap=200):
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding sentence keeps chunk under limit
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + " "
        else:
            # Save current chunk
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap
            current_chunk = current_chunk[-overlap:] + sentence + " "

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


if __name__ == "__main__":
    print("Extracting text...")
    text = extract_text_from_pdfs()

    print("Creating chunks...")
    chunks = chunk_text(text)

    print(f"Total chunks created: {len(chunks)}")
    print("Example chunk:\n")
    print(chunks[0][:500])
