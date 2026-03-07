"""
BEIET Bot — RAG Knowledge Base.

Provides document retrieval via ChromaDB and Google's embedding model.
"""

import os
from typing import List

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings
from google import genai

from bot.config import config


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for ChromaDB using Google's new genai SDK."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-004"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """Embeds a list of strings using the Gemini model."""
        if not input:
            return []
            
        embeddings = []
        # Process in batches or one-by-one based on the API limits
        for text in input:
            try:
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=text
                )
                embeddings.append(response.embeddings[0].values)
            except Exception as e:
                print(f"Error embedding text: {e}")
                # Create a zero-vector fallback or handle differently based on production needs
                # Assuming 768 dimensions for text-embedding-004
                embeddings.append([0.0] * 768)
                
        return embeddings


class RAGService:
    """Service to handle document retrieval for subjects."""

    def __init__(self, persist_dir: str = str(config.base_dir / "data" / "chroma_data")):
        self.persist_dir = persist_dir
        
        # Initialize the ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize Google embedding function
        self.embedding_fn = GeminiEmbeddingFunction(api_key=config.gemini_api_key)

    def get_collection(self, subject: str):
        """Retrieve or create a ChromaDB collection for the given subject."""
        subject_config = config.SUBJECTS.get(subject)
        if not subject_config:
            raise ValueError(f"Unknown subject: {subject}")
            
        collection_name = subject_config.collection_name
        
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": f"Knowledge base for {subject_config.name}"}
        )

    def retrieve_context(self, subject: str, query: str, n_results: int = 5) -> str:
        """
        Retrieves the most semantically relevant document chunks for a query.
        Returns a formatted string containing the context and citations.
        """
        if not config.gemini_api_key:
            return "⚠️ Búsqueda RAG deshabilitada (Falta API Key de Gemini en .env)."
            
        collection = self.get_collection(subject)
        
        # Handle empty collections gracefully
        if collection.count() == 0:
            return "No hay documentos cargados en la base de conocimientos para usar como referencia."
            
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results["documents"] or not results["documents"][0]:
                return "No se encontraron fragmentos relevantes en el material de estudio."
                
            formatted_context = "### Material de Referencia Recuperado:\n\n"
            
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                source = metadata.get("source", "Desconocido")
                page = metadata.get("page", "?")
                topic = metadata.get("topic", "")
                
                citation = f"[Fuente: {source}, p.{page}]"
                if topic:
                    citation += f" - Tema: {topic}"
                    
                formatted_context += f"{citation}\n{doc}\n\n---\n\n"
                
            return formatted_context.strip()
            
        except Exception as e:
            print(f"Error querying RAG: {e}")
            return "Ocurrió un error al consultar el material de estudio."


# Create a persistent singleton instance
rag_service = RAGService()
