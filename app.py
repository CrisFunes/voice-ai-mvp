# app.py
"""
Voice AI Agent MVP - Main Streamlit Application
Provides text and voice interfaces for Italian tax queries using RAG pipeline.
"""

import sys
import base64
from pathlib import Path
from datetime import datetime
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from loguru import logger

# Import project modules
from rag_engine import RAGEngine
from voice_handler import VoiceHandler
import config

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Remove default handler
logger.remove()

# Console logging (INFO and above)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

# File logging (DEBUG and above with rotation)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info("="*70)
logger.info("Voice AI Agent MVP - Application Starting")
logger.info("="*70)


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Assistente Fiscale AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Main title */
    .main-title {
        font-size: 2.8rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    /* Subtitle */
    .subtitle {
        color: #7f8c8d;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .status-ready {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
    }
    
    /* Answer box */
    .answer-box {
        background-color: #fff9e6;
        border-left: 4px solid #3498db;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        color: #2c3e50;
    }
    
    /* Source box */
    .source-box {
        background-color: #fff9e6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        color: #2c3e50;
    }
    
    /* Transcription display */
    .transcription {
        background-color: #fff9e6;
        border-left: 4px solid #f39c12;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-style: italic;
        color: #2c3e50;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve button styling */
    .stButton>button {
        width: 100%;
        border-radius: 0.5rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# CACHED RESOURCE INITIALIZATION
# ============================================================================

@st.cache_resource(show_spinner="🔄 Inizializzazione sistema RAG...")
def load_rag_engine():
    """
    Initialize and cache RAG engine.
    This is expensive (loads ChromaDB, initializes LLM client) so we cache it.
    """
    try:
        logger.info("Loading RAG Engine (cached)...")
        engine = RAGEngine()
        logger.success(f"RAG Engine loaded with {engine.collection.count()} chunks")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize RAG Engine: {e}")
        raise


@st.cache_resource(show_spinner="🎤 Inizializzazione sistema vocale...")
def load_voice_handler():
    """
    Initialize and cache voice handler.
    This initializes OpenAI client for ASR/TTS.
    """
    try:
        logger.info("Loading Voice Handler (cached)...")
        handler = VoiceHandler()
        logger.success("Voice Handler loaded successfully")
        return handler
    except Exception as e:
        logger.error(f"Failed to initialize Voice Handler: {e}")
        raise


# ============================================================================
# INITIALIZE ENGINES
# ============================================================================

try:
    rag_engine = load_rag_engine()
    voice_handler = load_voice_handler()
    initialization_success = True
    initialization_error = None
except Exception as e:
    logger.exception("Critical initialization failure")
    initialization_success = False
    initialization_error = str(e)


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<h1 class="main-title">🤖 Assistente Fiscale AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Demo MVP - Proof of Concept</p>', unsafe_allow_html=True)

# System status
if initialization_success:
    st.markdown(
        f'<span class="status-badge status-ready">✓ Sistema Pronto</span>'
        f'<span class="status-badge status-ready">📚 {rag_engine.collection.count()} Documenti</span>',
        unsafe_allow_html=True
    )
else:
    st.error(f"⚠️ Errore di inizializzazione: {initialization_error}")
    st.stop()


# ============================================================================
# DISCLAIMER
# ============================================================================

with st.expander("⚠️ IMPORTANTE - Leggi prima di usare", expanded=False):
    st.warning("""
    **Questo è un sistema dimostrativo e sperimentale.**
    
    - Le risposte sono generate da intelligenza artificiale e potrebbero contenere errori
    - NON sostituisce la consulenza professionale di un commercialista
    - Per questioni fiscali reali, consulta sempre un esperto qualificato
    - I documenti utilizzati sono solo a scopo dimostrativo
    
    **Privacy:**
    - Le registrazioni vocali sono temporanee e vengono eliminate automaticamente
    - Non vengono salvate informazioni personali
    - Le conversazioni non vengono archiviate
    """)

st.divider()


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'query_count' not in st.session_state:
    st.session_state.query_count = 0

if 'history' not in st.session_state:
    st.session_state.history = []


# ============================================================================
# TABS: TEXT vs VOICE
# ============================================================================

tab_text, tab_voice = st.tabs(["💬 Modalità Testo", "🎤 Modalità Voce"])


# ============================================================================
# TAB 1: TEXT MODE
# ============================================================================

with tab_text:
    st.subheader("💬 Chiedi via testo")
    
    # Text input
    question = st.text_area(
        "Fai una domanda fiscale in italiano:",
        placeholder="Esempio: Quando scade la dichiarazione IVA trimestrale?",
        height=100,
        key="text_input"
    )
    
    # Submit button
    col1, col2 = st.columns([3, 1])
    with col1:
        submit_text = st.button("🔍 Cerca Risposta", type="primary", key="text_submit")
    with col2:
        if st.button("🗑️ Pulisci", key="text_clear"):
            st.rerun()
    
    # Process query
    if submit_text:
        if not question or len(question.strip()) < 5:
            st.warning("⚠️ Per favore, scrivi una domanda più specifica (almeno 5 caratteri)")
        else:
            try:
                # Log query
                logger.info(f"[TEXT MODE] Processing query: {question[:50]}...")
                st.session_state.query_count += 1
                
                # Get answer
                with st.spinner("🔍 Sto cercando nei documenti fiscali..."):
                    result = rag_engine.get_answer(question)
                
                # Display answer
                st.markdown("---")
                st.markdown("### 📋 Risposta")
                st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                
                # Display sources
                if result['sources']:
                    st.markdown("### 📚 Fonti Consultate")
                    st.markdown('<div class="source-box">', unsafe_allow_html=True)
                    for i, source in enumerate(result['sources'], 1):
                        st.markdown(f"**{i}.** {source}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Metadata
                st.caption(
                    f"_Risposta generata usando {result['chunks_used']} frammenti di testo "
                    f"(confidenza: {result.get('confidence', 0):.0%})_"
                )
                
                # Add to history
                st.session_state.history.append({
                    'mode': 'text',
                    'question': question,
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'timestamp': datetime.now()
                })
                
                logger.success(f"[TEXT MODE] Answer delivered successfully")
                
            except Exception as e:
                logger.error(f"[TEXT MODE] Error processing query: {e}")
                st.error(f"⚠️ Si è verificato un errore: {str(e)}")
                st.info("💡 Suggerimenti:")
                st.markdown("""
                - Verifica che la domanda sia chiara e specifica
                - Prova a riformulare la domanda
                - Contatta il supporto se il problema persiste
                """)


# ============================================================================
# TAB 2: VOICE MODE
# ============================================================================

with tab_voice:
    st.subheader("🎤 Chiedi con la voce")
    
    st.info("👇 Clicca il pulsante per registrare la tua domanda vocale in italiano")
    
    # Audio recorder
    audio_bytes = audio_recorder(
        text="Clicca per registrare",
        recording_color="#e74c3c",
        neutral_color="#3498db",
        icon_size="2x",
        pause_threshold=2.0,
        sample_rate=16000,
        key="voice_recorder"
    )
    
    if audio_bytes:
        # Display recorded audio
        st.audio(audio_bytes, format="audio/wav")
        
        # Process button
        col1, col2 = st.columns([3, 1])
        with col1:
            analyze_voice = st.button("🔍 Analizza Domanda Vocale", type="primary", key="voice_submit")
        with col2:
            if st.button("🔄 Registra Nuovamente", key="voice_rerecord"):
                st.rerun()
        
        if analyze_voice:
            try:
                logger.info(f"[VOICE MODE] Processing audio ({len(audio_bytes)} bytes)")
                st.session_state.query_count += 1
                
                # Save audio temporarily
                temp_audio_path = config.TEMP_DIR / f"recording_{st.session_state.query_count}.wav"
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_bytes)
                
                logger.debug(f"Audio saved to: {temp_audio_path}")
                
                # STEP 1: Transcribe
                with st.spinner("🎧 Sto ascoltando la tua domanda..."):
                    transcript = voice_handler.transcribe(
                        str(temp_audio_path),
                        language="it",
                        prompt="IVA, IRES, IRAP, commercialista, dichiarazione, scadenza"
                    )
                
                # Display transcription
                st.markdown("### 🎯 Ho Capito:")
                st.markdown(f'<div class="transcription">"{transcript}"</div>', unsafe_allow_html=True)
                
                logger.info(f"[VOICE MODE] Transcription: {transcript}")
                
                # STEP 2: Get answer from RAG
                with st.spinner("📚 Cerco nei documenti fiscali..."):
                    result = rag_engine.get_answer(transcript)
                
                # Display answer (text)
                st.markdown("---")
                st.markdown("### 📋 Risposta")
                st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                
                # STEP 3: Synthesize speech
                with st.spinner("🔊 Genero la risposta vocale..."):
                    audio_response_path = voice_handler.synthesize(
                        result['answer'],
                        voice="alloy",
                        speed=1.0
                    )
                
                # Display audio player
                st.markdown("---")
                st.markdown("### 🔊 Ascolta la Risposta")
                
                # Read audio file and encode to base64 for HTML audio player
                with open(audio_response_path, "rb") as audio_file:
                    audio_b64 = base64.b64encode(audio_file.read()).decode()
                
                # HTML audio player with autoplay
                audio_html = f'''
                <audio controls autoplay style="width: 100%;">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                    Il tuo browser non supporta l'audio player.
                </audio>
                '''
                st.markdown(audio_html, unsafe_allow_html=True)
                
                # Display sources
                if result['sources']:
                    with st.expander("📚 Fonti Consultate"):
                        for i, source in enumerate(result['sources'], 1):
                            st.markdown(f"**{i}.** {source}")
                
                # Metadata
                st.caption(
                    f"_Risposta vocale generata da {result['chunks_used']} frammenti di testo "
                    f"(confidenza: {result.get('confidence', 0):.0%})_"
                )
                
                # Add to history
                st.session_state.history.append({
                    'mode': 'voice',
                    'question': transcript,
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'timestamp': datetime.now()
                })
                
                # Cleanup temp files
                try:
                    temp_audio_path.unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temp file: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")
                
                logger.success(f"[VOICE MODE] Complete pipeline executed successfully")
                
            except Exception as e:
                logger.error(f"[VOICE MODE] Error in voice pipeline: {e}")
                st.error(f"⚠️ Errore durante l'elaborazione vocale: {str(e)}")
                st.info("💡 Suggerimenti:")
                st.markdown("""
                - Assicurati di parlare chiaramente in italiano
                - Evita rumori di fondo durante la registrazione
                - Verifica che la domanda sia breve e specifica
                - Prova a registrare nuovamente
                """)


# ============================================================================
# SIDEBAR: SYSTEM INFO & HISTORY
# ============================================================================

with st.sidebar:
    st.markdown("### ℹ️ Informazioni Sistema")
    
    # System stats
    st.metric("Documenti Caricati", f"{rag_engine.collection.count():,}")
    st.metric("Query Eseguite", st.session_state.query_count)
    
    st.markdown("---")
    
    # Configuration info
    with st.expander("⚙️ Configurazione"):
        st.markdown(f"""
        **RAG Configuration:**
        - Chunk Size: {config.CHUNK_SIZE} chars
        - Overlap: {config.CHUNK_OVERLAP} chars
        - Top-K Results: {config.TOP_K_RESULTS}
        
        **LLM:**
        - Model: {config.LLM_MODEL}
        - Temperature: {config.LLM_TEMPERATURE}
        - Max Tokens: {config.LLM_MAX_TOKENS}
        
        **Voice:**
        - ASR Model: {config.ASR_MODEL}
        - TTS Model: {config.TTS_MODEL}
        - Voice: {config.TTS_VOICE}
        """)
    
    # Query history
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📜 Cronologia")
        
        for i, entry in enumerate(reversed(st.session_state.history[-5:]), 1):
            mode_icon = "💬" if entry['mode'] == 'text' else "🎤"
            with st.expander(f"{mode_icon} Query {len(st.session_state.history) - i + 1}"):
                st.caption(entry['timestamp'].strftime("%H:%M:%S"))
                st.markdown(f"**Q:** {entry['question'][:100]}...")
                st.markdown(f"**Fonti:** {len(entry['sources'])}")
    
    # Cleanup button
    st.markdown("---")
    if st.button("🧹 Pulisci File Temporanei"):
        deleted = voice_handler.cleanup_temp_files(max_age_hours=0)
        st.success(f"✓ {deleted} file eliminati")


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("🤖 Voice AI Agent MVP")

with col2:
    st.caption("⚙️ Powered by Claude AI")

with col3:
    st.caption("📅 Dicembre 2025")

# Final log
logger.info(f"App rendered successfully (queries: {st.session_state.query_count})")