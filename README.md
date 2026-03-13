# Materials Science RAG Chatbot (QUOKKA)

## Overview
This project develops a domain-specific chatbot for materials science using Retrieval-Augmented Generation (RAG).

The system answers questions using research PDFs instead of relying only on pretrained knowledge.

## Technologies Used
- Python
- FAISS Vector Database
- SentenceTransformers (Embeddings)
- TinyLlama Local LLM
- PyTorch GPU Acceleration

## Architecture
PDFs → Text Extraction → Chunking → Embeddings → FAISS → LLM → Answer + Sources

## How to Run

1. Create virtual environment:
python -m venv venv


2. Activate:
venv\Scripts\activate


3. Install dependencies:
pip install -r requirements.txt


4. Build index:
python build_index.py

5. Run chatbot:
python chatbot.py


## Features
- Local AI chatbot
- Domain-specific knowledge
- Source citation
- Offline execution