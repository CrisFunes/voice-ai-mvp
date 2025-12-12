"""
RAG Engine - Retrieval Augmented Generation
Handles document processing, embedding, storage, and retrieval
"""
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
import openai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger
import sys

import config
import prompts

# ============================================================================
# LOGGING SETUP
# ============================================================================
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format=config.LOG_FORMAT,
    level=config.LOG_LEVEL,
    colorize=True
)
logger.add(
    config.LOGS_DIR / "rag_engine_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)

# ============================================================================
# RAG ENGINE CLASS
# ============================================================================
class RAGEngine:
    """
    Retrieval Augmented Generation Engine
    
    Responsibilities:
    - Process PDF documents
    - Generate embeddings
    - Store in vector database
    - Semantic search
    - Context retrieval for LLM
    """
    
    def __init__(self):
        """Initialize RAG engine with vector store"""
        logger.info("Initializing RAG Engine...")
        
        # Setup OpenAI
        openai.api_key = config.OPENAI_API_KEY
        self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Setup ChromaDB
        logger.info(f"Connecting to ChromaDB at: {config.CHROMA_DIR}")
        self.chroma_client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR)
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="tax_documents_v2",
            metadata={"hnsw:space": "cosine"},
            embedding_function=None  # ← FIX: Disable ChromaDB's ONNX embeddings
        )
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        doc_count = self.collection.count()
        logger.info(f"RAG Engine initialized. Collection has {doc_count} chunks.")
        
        if doc_count == 0:
            logger.warning("⚠️ Vector database is empty! Run process_documents() to populate.")
    
    # ========================================================================
    # DOCUMENT PROCESSING
    # ========================================================================
    
    def process_documents(self, folder_path: Optional[Path] = None) -> Dict[str, int]:
        """
        Process all PDFs and TXTs in folder and store in vector DB
        
        Args:
            folder_path: Path to folder containing PDFs (default: config.DATA_DIR)
            
        Returns:
            Dictionary with processing statistics
        """
        if folder_path is None:
            folder_path = config.DATA_DIR
        
        logger.info(f"Starting document processing from: {folder_path}")
        
        # Find PDF and TXT files
        pdf_files = list(folder_path.glob("*.pdf"))
        txt_files = list(folder_path.glob("*.txt"))
        all_files = pdf_files + txt_files
        
        if not all_files:
            logger.warning(f"❌ No PDF or TXT files found in {folder_path}")
            logger.info("💡 Add PDFs or TXTs to data/documents/ folder and retry")
            return {"processed": 0, "chunks": 0, "errors": 0}
        
        logger.info(f"Found {len(all_files)} files to process ({len(pdf_files)} PDFs, {len(txt_files)} TXTs)")
        
        stats = {
            "processed": 0,
            "chunks": 0,
            "errors": 0
        }
        
        for file_path in all_files:
            logger.info(f"📄 Processing: {file_path.name}")
            
            try:
                # Extract text based on file type
                if file_path.suffix.lower() == '.pdf':
                    text = self._extract_text_from_pdf(file_path)
                elif file_path.suffix.lower() == '.txt':
                    text = self._extract_text_from_txt(file_path)
                else:
                    logger.warning(f"  ⚠️ Unsupported file type: {file_path.suffix}")
                    stats["errors"] += 1
                    continue
                
                # Chunk text
                chunks = self.text_splitter.split_text(text)
                logger.info(f"  Created {len(chunks)} chunks")
                
                # Process in batches (more efficient)
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    self._process_chunk_batch(batch, file_path, i)
                
                stats["processed"] += 1
                stats["chunks"] += len(chunks)
                logger.success(f"  ✅ {file_path.name} processed successfully")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing {file_path.name}: {e}")
                stats["errors"] += 1
        
        # Summary
        logger.info("=" * 70)
        logger.success(f"✅ Processing Complete!")
        logger.info(f"📄 Documents processed: {stats['processed']}/{len(all_files)}")
        logger.info(f"📦 Total chunks created: {stats['chunks']}")
        logger.info(f"❌ Errors: {stats['errors']}")
        logger.info(f"🗄️  Total chunks in database: {self.collection.count()}")
        logger.info("=" * 70)
        
        return stats
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            reader = PdfReader(str(pdf_path))
            text = ""
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num} ---\n{page_text}"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path.name}: {e}")
            raise
    
    def _extract_text_from_txt(self, txt_path: Path) -> str:
        """
        Extract text from TXT file
        
        Args:
            txt_path: Path to TXT file
            
        Returns:
            Extracted text
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 failed for {txt_path.name}, trying latin-1")
            with open(txt_path, 'r', encoding='latin-1') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"TXT extraction failed for {txt_path.name}: {e}")
            raise
    
    def _process_chunk_batch(self, chunks: List[str], file_path: Path, start_idx: int):
        """
        Process a batch of chunks: generate embeddings and store
        
        Args:
            chunks: List of text chunks
            file_path: Source file path
            start_idx: Starting index for chunk IDs
        """
        try:
            # Generate embeddings for batch
            embeddings = self._get_embeddings_batch(chunks)
            
            # Prepare IDs and metadata
            chunk_ids = [
                f"{file_path.stem}_chunk_{start_idx + i}"
                for i in range(len(chunks))
            ]
            
            metadatas = [
                {
                    "source": file_path.name,
                    "chunk_index": start_idx + i,
                    "total_chunks": len(chunks)
                }
                for i in range(len(chunks))
            ]
            
            # Store in ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=chunks,
                ids=chunk_ids,
                metadatas=metadatas
            )
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = self.openai_client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts (more efficient)
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = self.openai_client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================
def test_rag_engine():
    """Test RAG engine initialization and document processing"""
    logger.info("Testing RAG Engine...")
    
    # Initialize
    rag = RAGEngine()
    
    # Process documents
    stats = rag.process_documents()
    
    # Verify
    assert stats["processed"] > 0, "No documents processed!"
    assert stats["chunks"] > 0, "No chunks created!"
    
    logger.success("✅ RAG Engine test passed!")
    return rag


if __name__ == "__main__":
    test_rag_engine()