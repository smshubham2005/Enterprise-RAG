import os
from dataclasses import dataclass
from typing import List
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter, TokenTextSplitter

from core.config import get_settings
from core.logger import setup_logger
from services.vector_store import store_documents

logger = setup_logger("RAGService")

@dataclass
class ProcessResult:
    chunk_count: int
    embedding_count: int
    embedding_dimensions: int
    collection_name: str

class RAGService:
    """
    Service to handle document ingestion workflows.
    
    Architectural Design Note on Splitters for Interviews:
    - RecursiveCharacterTextSplitter (Chosen): Splits by a list of characters (default: ["\n\n", "\n", " ", ""])
      recursively. This keeps paragraphs, sentences, and words together as much as possible, preserving
      semantic cohesion.
    - CharacterTextSplitter: Splits on a single separator (e.g. "\n\n"). This is too simple for real-world PDFs
      as it often creates chunks that are too large or too small, leading to poor RAG recall.
    - TokenTextSplitter: Splits based on LLM token counts directly. Good for preventing context window overflow,
      but can split text in the middle of sentences or words, degrading semantic meaning.
      
    Future Scalability Refactoring:
    If this service grows, it should be split into:
    1. `DocumentLoader` Interface (e.g., PDFLoader, WordLoader, URLLoader)
    2. `TextSplitter` Interface (to swap splitting algorithms easily)
    3. `VectorStorageService` (handling DB writes and collection isolation)
    """
    def __init__(self):
        settings = get_settings()
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_text_from_pdf(self, file_path: str, filename: str) -> List[Document]:
        """
        Extracts text page-by-page from a PDF and attaches metadata.
        Robust to corrupted, empty, or encrypted files.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"PDF file not found at {file_path}")

        documents = []
        logger.info(f"Extracting text from PDF: {filename}")

        try:
            reader = PdfReader(file_path)
            
            # 1. Exception Handling: Encrypted PDF Check
            if reader.is_encrypted:
                logger.error(f"Failed to process {filename}: PDF is encrypted.")
                raise ValueError("The uploaded PDF is encrypted. Please upload an unencrypted file.")
            
            # 2. Exception Handling: Empty PDF Check
            total_pages = len(reader.pages)
            if total_pages == 0:
                logger.error(f"Failed to process {filename}: PDF has 0 pages.")
                raise ValueError("The uploaded PDF is empty.")

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if not text or not text.strip():
                        logger.warning(f"No readable text found on page {page_num} of {filename}")
                        continue
                    
                    # Store rich metadata for citations
                    metadata = {
                        "source_file": filename,
                        "page": page_num,
                        "total_pages": total_pages
                    }
                    documents.append(Document(page_content=text, metadata=metadata))
                except Exception as page_err:
                    logger.warning(f"Error reading page {page_num} in {filename}: {page_err}")
                    continue

            # 3. Exception Handling: Scanned/Unreadable PDF Check
            if not documents:
                logger.error(f"Failed to process {filename}: No readable text extracted.")
                raise ValueError("PDF does not contain readable text. It may be scanned or corrupted.")

            logger.info(f"Extracted {len(documents)} pages from {filename}")
            return documents

        except ValueError as ve:
            raise ve
        except Exception as e:
            logger.error(f"Error parsing PDF file {filename}: {str(e)}")
            raise ValueError("Corrupted PDF file or unsupported PDF structure.")

    def chunk_documents(self, documents: List[Document], filename: str, document_id: str = "") -> List[Document]:
        """
        Chunks text and attaches ID/source metadata.
        """
        logger.info(f"Chunking {len(documents)} pages from {filename}")
        try:
            chunks = self.text_splitter.split_documents(documents)
            
            prefix = document_id or filename
            # Attach chunk-specific metadata
            for idx, chunk in enumerate(chunks):
                page = chunk.metadata.get("page", 1)
                chunk.metadata["chunk_id"] = f"{prefix}_p{page}_c{idx}"
                chunk.metadata["section_title"] = f"Page {page} Section"

            logger.info(f"Created {len(chunks)} chunks for {filename}")
            return chunks
        except Exception as e:
            logger.error(f"Failed to chunk documents for {filename}: {e}")
            raise RuntimeError(f"Failed to chunk documents: {e}")


def process_document(file_path: str, filename: str, document_id: str, storage_filename: str) -> ProcessResult:
    """
    Public API interface to process a document fully: loader -> splitter -> vector store.
    """
    settings = get_settings()
    service = RAGService()
    
    # 1. Extract
    docs = service.extract_text_from_pdf(file_path, filename)
    
    # 2. Chunk
    chunks = service.chunk_documents(docs, filename, document_id=document_id)
    
    # 3. Store in Vector Store
    logger.info(f"Storing {len(chunks)} chunks in ChromaDB...")
    try:
        stored_count = store_documents(chunks, filename, document_id, storage_filename)
        logger.info(f"Successfully indexed {stored_count} chunks.")
    except Exception as e:
        logger.error(f"Failed to store documents in ChromaDB: {e}")
        raise RuntimeError(f"ChromaDB write failure: {e}")
        
    return ProcessResult(
        chunk_count=len(chunks),
        embedding_count=len(chunks),
        embedding_dimensions=768, # Google embedding-001 vector size
        collection_name=settings.chroma_collection_name
    )

