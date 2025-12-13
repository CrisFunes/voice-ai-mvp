"""
Configuration Management
Handles API keys, paths, and model settings
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# API KEYS - CRITICAL
# ============================================================================

# Primary LLM (Anthropic)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_ANTHROPIC = os.getenv("USE_ANTHROPIC", "true").lower() == "true"

# Fallback LLM (OpenAI)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI_FALLBACK = os.getenv("USE_OPENAI_FALLBACK", "false").lower() == "true"

if USE_ANTHROPIC:
    LLM_MODEL = "claude-3-5-sonnet-20240620"
    LLM_PROVIDER = "anthropic"
elif USE_OPENAI_FALLBACK:
    LLM_MODEL = "gpt-4o"  # or "gpt-4-turbo"
    LLM_PROVIDER = "openai"
else:
    raise ValueError("No LLM provider configured")


# Validate keys on import
if not OPENAI_API_KEY:
    raise ValueError(
        "❌ OPENAI_API_KEY not found in .env file!\n"
        "Create .env file with: OPENAI_API_KEY=sk-proj-..."
    )

if not ANTHROPIC_API_KEY:
    raise ValueError(
        "❌ ANTHROPIC_API_KEY not found in .env file!\n"
        "Create .env file with: ANTHROPIC_API_KEY=sk-ant-..."
    )

# ============================================================================
# PATHS
# ============================================================================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "documents"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
TEMP_DIR = PROJECT_ROOT / "temp"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for directory in [DATA_DIR, CHROMA_DIR, TEMP_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# RAG CONFIGURATION
# ============================================================================
# Document chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "3"))

# Embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small default

# ============================================================================
# LLM CONFIGURATION
# ============================================================================
# LLM_MODEL = "claude-3-5-sonnet-20240620"
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))

# ============================================================================
# VOICE CONFIGURATION
# ============================================================================
# ASR (Speech-to-Text)
ASR_MODEL = "whisper-1"
ASR_LANGUAGE = "it"  # Italian

# TTS (Text-to-Speech)
TTS_MODEL = "tts-1"  # Can upgrade to tts-1-hd for production
TTS_VOICE = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
TTS_SPEED = 1.0

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database URL (can be overridden by environment variable)
# Version B: SQLite (local file)
# Version A: PostgreSQL (will set DATABASE_URL env var)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./demo_v2.db"  # Default to SQLite
)

# Service mode (mock vs real implementations)
SERVICE_MODE = os.getenv("SERVICE_MODE", "mock")  # "mock" or "real"

# ============================================================================
# DISPLAY CONFIGURATION ON IMPORT
# ============================================================================
print("=" * 70)
print("🚀 Voice AI Agent MVP - Configuration Loaded")
print("=" * 70)
print(f"📁 Data Directory: {DATA_DIR}")
print(f"🗄️  ChromaDB Directory: {CHROMA_DIR}")
print(f"📝 Chunk Size: {CHUNK_SIZE} chars (overlap: {CHUNK_OVERLAP})")
print(f"🔍 Retrieval: Top {TOP_K_RESULTS} results")
print(f"🤖 LLM: {LLM_MODEL}")
print(f"🎤 ASR: {ASR_MODEL} ({ASR_LANGUAGE})")
print(f"🔊 TTS: {TTS_MODEL} (voice: {TTS_VOICE})")
print("=" * 70)