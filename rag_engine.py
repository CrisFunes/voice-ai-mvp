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
from tenacity import retry, stop_after_attempt, wait_exponential
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
        
        if config.LLM_PROVIDER == "anthropic":
            from anthropic import Anthropic
            self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self.llm_provider = "anthropic"
        elif config.LLM_PROVIDER == "openai":
            import openai
            openai.api_key = config.OPENAI_API_KEY
            self.llm_provider = "openai"

        # Setup OpenAI
        openai.api_key = config.OPENAI_API_KEY
        self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Setup ChromaDB
        logger.info(f"Connecting to ChromaDB at: {config.CHROMA_DIR}")
        self.chroma_client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR)
        )
        # Setup Anthropic client (ADD THIS)
        from anthropic import Anthropic
        self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        logger.info(f"Anthropic client initialized with model: {config.LLM_MODEL}")
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
    
    def query(self, question: str, n_results: int = None) -> Tuple[List[str], List[dict]]:
        if n_results is None:
            n_results = config.TOP_K_RESULTS
        
        if not question or len(question.strip()) < 3:
            raise ValueError("Question too short (min 3 chars)")
        
        logger.info(f"Searching for: {question[:50]}...")
        
        # Generate query embedding
        query_embedding = self._get_embedding(question)
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Validate results
        chunks = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        
        logger.info(f"Found {len(chunks)} relevant chunks")
        
        return chunks, metadatas
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, prompt: str) -> str:
        """
        Call Claude API with retry logic
        
        Args:
            prompt: Complete prompt with context and question
            
        Returns:
            Generated response text
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        if self.llm_provider == "anthropic":
            # Existing Anthropic code
            message = self.anthropic_client.messages.create(...)
            return message.content[0].text
        
        elif self.llm_provider == "openai":
            # OpenAI fallback
            response = openai.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=config.LLM_TEMPERATURE
            )
            return response.choices[0].message.content

        try:
            logger.debug(f"Calling Claude with prompt length: {len(prompt)} chars")
            
            message = self.anthropic_client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=config.LLM_TEMPERATURE,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response = message.content[0].text
            logger.success(f"Claude response received: {len(response)} chars")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise  # Let tenacity handle retry

    def get_answer(self, question: str) -> Dict:
        """Complete RAG pipeline: question → answer with sources"""
        
        # Validate
        if not question or len(question.strip()) < 5:
            raise ValueError("Domanda troppo breve (minimo 5 caratteri)")
        
        logger.info(f"Processing query: {question[:50]}...")
        
        # Retrieve
        try:
            chunks, metadatas = self.query(question)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                'answer': prompts.NO_RESULTS_RESPONSE,
                'sources': [],
                'chunks_used': 0,
                'error': str(e)
            }
        
        # Handle no results
        if not chunks:
            logger.warning("No relevant chunks found")
            return {
                'answer': prompts.NO_RESULTS_RESPONSE,
                'sources': [],
                'chunks_used': 0
            }
        
        # Build context
        context = "\n\n---\n\n".join([
            f"DOCUMENTO: {meta.get('source', 'Unknown')}\n{chunk}"
            for chunk, meta in zip(chunks, metadatas)
        ])
        
        # Build prompt (use prompts.SYSTEM_PROMPT_V1 from prompts.py)
        prompt = prompts.SYSTEM_PROMPT_V1.format(
            context=context,
            question=question
        )
        
        # Generate answer
        try:
            answer = self._call_llm(prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                'answer': "Errore nella generazione della risposta. Riprova.",
                'sources': [],
                'chunks_used': 0,
                'error': str(e)
            }
        
        # Extract sources
        sources = list(set([meta.get('source', 'Unknown') for meta in metadatas]))
        
        logger.success(f"Answer generated using {len(chunks)} chunks from {len(sources)} sources")
        
        return {
            'answer': answer,
            'sources': sources,
            'chunks_used': len(chunks),
            'confidence': self._calculate_confidence(chunks, question)  # Optional
        }

    def _calculate_confidence(self, chunks: List[str], question: str) -> float:
        """Optional: estimate confidence based on similarity scores"""
        # Simple heuristic: if we got results, confidence = 0.8
        # Production: use actual similarity scores from ChromaDB
        return 0.8 if chunks else 0.0


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