# Voice AI Agent MVP

AI-powered voice assistant for Italian fiscal queries using RAG (Retrieval-Augmented Generation).

## Overview

This MVP demonstrates an intelligent fiscal advisory system that can answer questions about Italian tax law by:
- Processing fiscal documents into searchable embeddings
- Retrieving relevant information using semantic search
- Generating accurate responses in Italian using Claude AI
- Supporting both text and voice interactions

## Features

- 📚 **RAG Pipeline**: Processes Italian fiscal documents (PDFs) into vector embeddings
- 🤖 **AI Integration**: Uses Claude 3.5 Sonnet for intelligent response generation
- 🎤 **Voice Input**: Speech-to-text using OpenAI Whisper (Italian language)
- 🔊 **Voice Output**: Text-to-speech using OpenAI TTS (Italian language)
- 💬 **Text Interface**: Clean web-based chat interface
- 📖 **Source Citation**: All responses cite their source documents
- ⚠️ **Legal Disclaimers**: Appropriate warnings on all advice

## Prerequisites

- Python 3.10 or higher
- Windows 10/11, macOS, or Linux
- OpenAI API key
- Anthropic API key

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

### Step 3: Upgrade pip (Important for Windows)

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

**Windows Users:** If you encounter NumPy installation errors, see [Troubleshooting](#troubleshooting) below.

### Step 5: Configure API Keys

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

**Important:** Never commit your `.env` file to version control.

### Step 6: Process Documents

Place your Italian fiscal PDF documents in `data/documents/`, then run:

```bash
python setup_rag.py
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

## Project Structure

```
voice-ai-mvp/
├── app.py                      # Main Streamlit application
├── rag_engine.py               # RAG pipeline logic
├── voice_handler.py            # Speech-to-text and text-to-speech
├── prompts.py                  # System prompts and templates
├── config.py                   # Configuration management
├── demo_scenarios.py           # Pre-tested demo queries
├── setup_rag.py                # Document processing script
├── requirements.txt            # Python dependencies
├── .env                        # API keys (gitignored)
├── .env.example                # Template for .env
├── .gitignore                  # Git exclusions
├── README.md                   # This file
├── data/
│   └── documents/              # Input PDFs (add your documents here)
├── chroma_db/                  # Vector database (generated)
└── temp/                       # Temporary audio files (gitignored)
```

## Usage

### Text Mode

1. Open the application in your browser
2. Navigate to the "Text" tab
3. Type your question in Italian (e.g., "Quando scade la dichiarazione IVA?")
4. Click "Submit" or press Enter
5. View the answer with source citations

### Voice Mode

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

<!-- ## Configuration

Edit `config.py` to customize:

- **Model Selection**: Change Claude or embedding models
- **Chunk Size**: Adjust document chunking (default: 1000 chars)
- **Search Results**: Number of retrieved chunks (default: 3)
- **File Paths**: Document and database locations -->

## Troubleshooting

### Windows: NumPy Installation Errors

**Problem:** NumPy fails to compile, error about missing C compiler.

**Solution:**

```bash
# 1. Upgrade pip tools
python -m pip install --upgrade pip setuptools wheel

# 2. Install NumPy separately first (uses pre-compiled wheel)
pip install numpy

# 3. Then install other dependencies
pip install -r requirements.txt
```

### Windows: ChromaDB pulsar-client Error

**Problem:** `ERROR: No matching distribution found for pulsar-client>=3.1.0`

**Solution:** This is already handled in `requirements.txt` by using `chromadb==0.4.15` which doesn't require pulsar-client.

If you still encounter this:

```bash
# Uninstall and clear cache
pip uninstall chromadb -y
pip cache purge

# Reinstall specific version
pip install chromadb==0.4.15
```

### API Key Errors

**Problem:** `AuthenticationError` or `API key not found`

**Solution:**

1. Verify `.env` file exists in project root
2. Check API keys are correct (no extra spaces)
3. Restart the application after changing `.env`

### Document Processing Fails

**Problem:** PDFs don't process or produce errors

**Solutions:**

- Ensure PDFs are text-based (not scanned images)
- Check for Italian character encoding issues
- Try processing one PDF at a time for debugging
- Check PDF file isn't password-protected

### Microphone Not Working

**Problem:** Browser doesn't detect microphone

**Solutions:**

1. Grant microphone permissions when prompted
2. Check browser settings (Privacy & Security → Microphone)
3. Use Chrome or Firefox (better WebRTC support)
4. Localhost automatically allows microphone access

<!-- ## Testing

Run the demo scenarios to verify everything works:

```python
# In Python console or Jupyter
from demo_scenarios import DEMO_QUERIES
from rag_engine import RAGEngine

rag = RAGEngine()
for name, query in DEMO_QUERIES.items():
    print(f"\n{name}: {query}")
    result = rag.get_answer(query)
    print(f"Answer: {result['answer'][:100]}...")
``` -->

## API Costs

Estimated costs for MVP testing (50 queries):

- **Document Processing (one-time)**: ~$0.01
- **Query Embeddings**: ~$0.001 per query
- **Claude API**: ~$0.045 per query (500 tokens avg)
- **Whisper ASR**: ~$0.006 per minute
- **TTS**: ~$0.015 per 1K characters

**Total for 50 test queries**: ~$3-5

## Production Considerations

This MVP is designed for demonstration. For production deployment:

### Recommended Changes

1. **Frontend**: Migrate from Streamlit to React/Next.js
2. **Backend**: Use FastAPI for REST API
3. **Vector DB**: Migrate to Pinecone or PostgreSQL for scale
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

## Contributing

This is an MVP project. For issues or improvements:

1. Document the issue/enhancement
2. Test locally
3. Submit with clear description
4. Include before/after examples



## Quick Start Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] pip upgraded to latest version
- [ ] Dependencies installed from requirements.txt
- [ ] .env file created with API keys
- [ ] PDF documents added to data/documents/
- [ ] Documents processed with setup_rag.py
- [ ] Application runs with `streamlit run app.py`
- [ ] Text queries working
- [ ] Voice recording working
- [ ] Demo scenarios tested

**Questions?** Check the [Troubleshooting](#troubleshooting) section above.