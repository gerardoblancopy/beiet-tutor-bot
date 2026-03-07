"""
BEIET Bot — Document Ingestion Script.

CLI tool to process PDFs and inject them into ChromaDB.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the project root to sys.path so we can import from bot.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm

from bot.config import config
from bot.core.rag import rag_service


def extract_topic_from_filename(filename: str) -> str:
    """Extract a clean topic name from a pdf filename."""
    # Assuming standard names like "Unidad_1_Programacion_Lineal.pdf"
    clean_name = os.path.splitext(filename)[0]
    return clean_name.replace("_", " ").title()


def ingest_directory(subject: str, directory_path: str):
    """Read all PDFs in a directory and push chunks to ChromaDB."""
    
    if subject not in config.SUBJECTS:
        print(f"Error: Unknown subject '{subject}'. Valid options are: {list(config.SUBJECTS.keys())}")
        return

    dir_path = Path(directory_path)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Error: Directory '{dir_path}' does not exist.")
        return

    pdf_files = list(dir_path.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{dir_path}'.")
        return

    if not config.gemini_api_key:
        print("Error: GEMINI_API_KEY environment variable is not set. Cannot generate embeddings.")
        return

    # Semantic Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )

    collection = rag_service.get_collection(subject)
    
    # Check what's already in the collection (naive duplicate prevention by source)
    existing_docs = {}
    try:
        # Get existing metadata to prevent re-ingesting
        existing_results = collection.get(include=["metadatas"])
        if existing_results and existing_results["metadatas"]:
            for meta in existing_results["metadatas"]:
                if meta and "source" in meta:
                    existing_docs[meta["source"]] = True
    except Exception as e:
        print(f"Could not retrieve existing documents: {e}")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        
        # Skip if already ingested
        if filename in existing_docs:
            print(f"Skipping '{filename}' (Already in ChromaDB).")
            continue
            
        print(f"\nProcessing '{filename}'...")
        
        topic = extract_topic_from_filename(filename)
        
        reader = PdfReader(str(pdf_path))
        chunks = []
        metadatas = []
        ids = []
        
        chunk_counter = 0
        
        for i, page in enumerate(tqdm(reader.pages, desc="Extracting & Chunking pages")):
            text = page.extract_text()
            if not text:
                continue
                
            page_chunks = text_splitter.split_text(text)
            
            for c in page_chunks:
                # Clean up extracted text
                clean_chunk = " ".join(c.split())
                
                if len(clean_chunk) < 50:  # Skip chunks that are too small and noisy
                    continue
                    
                chunks.append(clean_chunk)
                metadatas.append({
                    "source": filename,
                    "page": i + 1,
                    "topic": topic
                })
                ids.append(f"{filename}_p{i + 1}_chunk{chunk_counter}")
                chunk_counter += 1
                
        if not chunks:
            print(f"Warning: No valid text extracted from '{filename}'.")
            continue
            
        print(f"Generated {len(chunks)} chunks. Sending to ChromaDB (This might take a while)...")
        
        # Upsert in batches of 100 to avoid API rate limits
        batch_size = 100
        for i in tqdm(range(0, len(chunks), batch_size), desc="Embedding & Upserting"):
            batch_chunks = chunks[i : i + batch_size]
            batch_metadatas = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            
            try:
                collection.upsert(
                    documents=batch_chunks,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
            except Exception as e:
                print(f"Error during upsert: {e}")

    print(f"\n✅ Finished processing '{dir_path}'. Total documents in collection: {collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDF documents into BEIET's ChromaDB RAG Knowledge Base.")
    parser.add_argument("--subject", type=str, required=True, help=f"Subject name ({list(config.SUBJECTS.keys())}).")
    parser.add_argument("--path", type=str, required=True, help="Path to the directory containing PDFs.")
    
    args = parser.parse_args()
    
    # Let's double check path resolves to absolutely correct relative location
    abs_path = Path(args.path).absolute()
    
    print("=" * 50)
    print(f"BEIET Document Ingestion Pipeline")
    print(f"Subject: {config.SUBJECTS.get(args.subject).name if args.subject in config.SUBJECTS else 'UNKNOWN'}")
    print(f"Source Directory: {abs_path}")
    print("=" * 50)
    
    ingest_directory(args.subject, str(abs_path))
