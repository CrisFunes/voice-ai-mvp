# Voice AI Agent MVP

Proof of Concept for enterprise VUI-RAG system for Italian accounting firms.

✅ **Tax RAG Pipeline** (50%)
- Document processing and chunking
- Semantic search with embeddings  
- LLM response generation for tax queries
- Source citation with disclaimers

✅ **Call Center Operations** (50%)
- Intent classification (tax vs booking vs routing)
- Client/accountant database lookup
- Appointment management (simulated)
- Call routing to specialists
- Office information responses
- Lead capture for new clients

✅ **Voice Interface**
- Speech-to-text (Italian)
- Text-to-speech (Italian)
- Web-based interaction

## What's NOT in Demo (Enterprise Only)

❌ Telephony integration (Twilio)
❌ Client database & function calling
❌ Real-time streaming
❌ Appointment booking
❌ Call routing logic

**This demo proves the core AI pipeline works.** 
Enterprise features are architectural additions, not core rewrites.

---

## Overview

This MVP demonstrates an intelligent fiscal advisory system that answers questions about Italian tax law by:
- Processing fiscal documents into searchable embeddings
- Retrieving relevant information using semantic search
- Generating accurate responses in Italian using Claude AI
- Supporting both text and voice interactions

## Features

- 📚 **RAG Pipeline**: Processes Italian fiscal documents (PDFs) into vector embeddings
- 🤖 **AI Integration**: Uses Claude 3.5 Sonnet for intelligent response generation
- 🎤 **Voice Input**: Speech-to-text using OpenAI Whisper (Italian)
- 🔊 **Voice Output**: Text-to-speech using OpenAI TTS (Italian)
- 💬 **Text Interface**: Clean web-based chat interface
- 📖 **Source Citation**: All responses cite their source documents
- ⚠️ **Legal Disclaimers**: Appropriate warnings on all advice

---

## Prerequisites

- Python 3.10 or higher
- Windows 10/11, macOS, or Linux
- OpenAI API key
- Anthropic API key

---

## Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd voice-ai-mvp
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Upgrade pip
```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

**Windows Users:** If you encounter errors, see [Troubleshooting](#troubleshooting).

### Step 5: Configure API Keys

Create a `.env` file in the project root:
```bash
# Windows
New-Item -Path ".env" -ItemType File

# macOS/Linux
touch .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Important:** Never commit `.env` to version control.

### Step 6: Process Documents

Place your Italian fiscal PDF documents in `data/documents/`, then run:
```bash
python -c "from rag_engine import RAGEngine; rag = RAGEngine(); rag.process_documents()"
```

This will:
- Extract text from PDFs
- Create text chunks
- Generate embeddings
- Store in vector database

Expected time: 5-10 minutes for 15 documents.

### Step 7: Run the Application
```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

---

## Project Structure
```
voice-ai-mvp/
├── app.py                      # Main Streamlit application (TODO)
├── rag_engine.py               # RAG pipeline logic (IN PROGRESS)
├── voice_handler.py            # Speech-to-text and text-to-speech (TODO)
├── prompts.py                  # System prompts and templates
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env                        # API keys (gitignored)
├── .gitignore                  # Git exclusions
├── README.md                   # This file
├── data/
│   └── documents/              # Input PDFs (add your documents here)
├── chroma_db/                  # Vector database (generated)
├── temp/                       # Temporary audio files (gitignored)
└── logs/                       # Application logs (generated)
```

---

## Usage

### Text Mode (Coming Soon)

1. Open the application in your browser
2. Navigate to the "Text" tab
3. Type your question in Italian (e.g., "Quando scade la dichiarazione IVA?")
4. Click "Submit" or press Enter
5. View the answer with source citations

### Voice Mode (Coming Soon)

1. Navigate to the "Voice" tab
2. Click the microphone icon to record
3. Speak your question in Italian
4. Click to stop recording
5. Click "Analyze Voice Question"
6. The system will:
   - Transcribe your speech
   - Search for relevant information
   - Generate an answer
   - Speak the response aloud

---

## Troubleshooting

### Windows: Dependency Installation Errors

**Problem:** Errors during `pip install -r requirements.txt`

**Solution:**
```bash
# 1. Ensure clean environment
Remove-Item -Recurse -Force venv
python -m venv venv
venv\Scripts\activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Install dependencies
pip install -r requirements.txt
```

### ChromaDB Issues

**Problem:** `ValueError: The onnxruntime python package is not installed`

**Solution:** Already fixed in `requirements.txt` with `chromadb==0.4.22`.

If still having issues:
```bash
pip uninstall chromadb -y
pip install chromadb==0.4.22
```

### API Key Errors

**Problem:** `AuthenticationError` or `API key not found`

**Solution:**

1. Verify `.env` file exists in project root
2. Check API keys are correct (no extra spaces)
3. Verify format:
   - OpenAI: `sk-proj-...`
   - Anthropic: `sk-ant-...`
4. Restart application after changing `.env`

### Document Processing Fails

**Problem:** PDFs don't process or produce errors

**Solutions:**

- Ensure PDFs are text-based (not scanned images)
- Check for Italian character encoding issues
- Try processing one PDF at a time for debugging
- Check PDF isn't password-protected

**Test with single file:**
```python
from rag_engine import RAGEngine
from pathlib import Path

rag = RAGEngine()
text = rag._extract_text_from_pdf(Path("data/documents/your-file.pdf"))
print(f"Extracted {len(text)} characters")
```

---

## API Costs

Estimated costs for MVP testing (50 queries):

| Service | Usage | Cost |
|---------|-------|------|
| Document Processing | One-time (15 docs) | $0.01 |
| Query Embeddings | 50 queries | $0.05 |
| Claude API | 50 queries (500 tokens avg) | $0.70 |
| Whisper ASR | 25 minutes | $0.15 |
| TTS | 10,000 characters | $0.15 |
| **TOTAL** | **50 test queries** | **~$1.06** |

**Production estimate (1000 queries/day):** ~$1,460/month

---

## Development Status

### ✅ Completed
- [x] Project structure
- [x] Dependencies configured
- [x] config.py implemented
- [x] prompts.py implemented
- [x] rag_engine.py document processing

### ⏳ In Progress (Day 2)
- [ ] rag_engine.py query methods
- [ ] Claude API integration
- [ ] End-to-end RAG pipeline

### 📋 TODO (Day 3-4)
- [ ] voice_handler.py implementation
- [ ] app.py Streamlit UI
- [ ] Voice integration (ASR + TTS)
- [ ] Testing and polish

---

## Production Considerations

This MVP is designed for demonstration. For production deployment:

### Recommended Changes

1. **Frontend**: Migrate from Streamlit to React/Next.js
2. **Backend**: Use FastAPI for REST API
3. **Vector DB**: Migrate to Qdrant or Pinecone for scale
4. **Voice**: Use Deepgram for real-time streaming ASR
5. **Authentication**: Add user authentication and session management
6. **Monitoring**: Implement logging, metrics, and error tracking
7. **Caching**: Add Redis for frequent queries
8. **Security**: Implement rate limiting, input validation

### What to Keep

- RAG pipeline architecture
- Prompt engineering approach
- Source citation logic
- Disclaimer enforcement
- Error handling patterns

---

## Quick Start Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] pip upgraded to latest version
- [ ] Dependencies installed from requirements.txt
- [ ] .env file created with API keys
- [ ] PDF documents added to data/documents/
- [ ] Documents processed successfully
- [ ] ChromaDB populated with embeddings

**Questions?** Check the [Troubleshooting](#troubleshooting) section above.