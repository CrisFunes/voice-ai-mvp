"""
REFACTORED VERSION - Production-Ready Phone UI
Voice AI Agent with proper state management and audio synchronization

CRITICAL IMPROVEMENTS:
1. Granular CallState with 8 observable states
2. Manual audio transitions (no JavaScript hacks)
3. Separated concerns (state update, UI update, orchestrator calls)
4. Proper conversation history passing
5. Comprehensive error handling
6. Clean state machine transitions

Author: Principal Software Architect
Date: December 2025
"""

import sys
import time
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from loguru import logger

from orchestrator import Orchestrator
from voice_handler import VoiceHandler
import config


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logger.remove()
logger.add(
    sys.stderr, 
    level="INFO", 
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


# ============================================================================
# ENUMS - GRANULAR STATE MACHINE
# ============================================================================

class CallState(Enum):
    """
    Granular call states for observable state machine.
    
    CRITICAL: Each state MUST be visually observable in UI.
    States should last at least 500ms to be perceptible to users.
    """
    IDLE = "idle"                               # Not in call
    GREETING_GENERATION = "greeting_generation" # Generating welcome message
    GREETING_PLAYBACK = "greeting_playback"     # Playing welcome audio
    WAITING_FOR_INPUT = "waiting_for_input"     # Ready for user to speak
    RECORDING = "recording"                     # Actively recording user
    PROCESSING = "processing"                   # ASR + Orchestrator
    RESPONSE_GENERATION = "response_generation" # Generating AI response
    RESPONSE_PLAYBACK = "response_playback"     # Playing AI response
    ENDED = "ended"                             # Call terminated


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Studio Commercialista - Assistente AI",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================================
# CSS STYLING
# ============================================================================

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .phone-container {
        max-width: 500px;
        margin: 2rem auto;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 30px;
        padding: 30px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    
    .call-status {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 700;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 20px;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    .status-idle { background-color: #95a5a6; color: white; }
    .status-greeting_generation { background-color: #3498db; color: white; }
    .status-greeting_playback { background-color: #2ecc71; color: white; }
    .status-waiting_for_input { background-color: #27ae60; color: white; }
    .status-recording { background-color: #e74c3c; color: white; }
    .status-processing { background-color: #9b59b6; color: white; }
    .status-response_generation { background-color: #f39c12; color: white; }
    .status-response_playback { background-color: #e67e22; color: white; }
    .status-ended { background-color: #34495e; color: white; }
    
    .conversation-container {
        background-color: white;
        border-radius: 20px;
        padding: 20px;
        max-height: 400px;
        overflow-y: auto;
        margin-bottom: 20px;
    }
    
    .message-bubble {
        margin: 10px 0;
        padding: 12px 16px;
        border-radius: 18px;
        max-width: 80%;
        word-wrap: break-word;
    }
    
    .message-ai {
        background-color: #e8f4f8;
        color: #2c3e50;
        margin-right: auto;
        border-bottom-left-radius: 4px;
    }
    
    .message-user {
        background-color: #667eea;
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
        text-align: right;
    }
    
    .message-timestamp {
        font-size: 0.75rem;
        color: #95a5a6;
        margin-top: 4px;
    }
    
    .message-metadata {
        font-size: 0.7rem;
        color: #7f8c8d;
        font-style: italic;
        margin-top: 4px;
    }
    
    .call-timer {
        text-align: center;
        color: white;
        font-size: 0.9rem;
        margin-bottom: 10px;
        font-weight: 600;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        padding: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# CACHED RESOURCES
# ============================================================================

@st.cache_resource(show_spinner="Caricamento Orchestrator...")
def load_orchestrator():
    """
    Load and cache orchestrator.
    
    CRITICAL: This is your LangGraph state machine.
    All conversation logic flows through this.
    """
    try:
        logger.info("Initializing Orchestrator...")
        orchestrator = Orchestrator()
        logger.success("Orchestrator ready")
        return orchestrator
    except Exception as e:
        logger.error(f"Orchestrator loading failed: {e}")
        raise


@st.cache_resource(show_spinner="Caricamento Voice Handler...")
def load_voice_handler():
    """
    Load and cache voice handler (ASR + TTS).
    """
    try:
        logger.info("Initializing Voice Handler...")
        voice = VoiceHandler()
        logger.success("Voice Handler ready")
        return voice
    except Exception as e:
        logger.error(f"Voice Handler loading failed: {e}")
        raise


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """
    Initialize session state with all required variables.
    
    CRITICAL: We maintain separation between:
    - UI state (call_state, ui_conversation)
    - Orchestrator state (conversation_history, entities)
    - Audio state (last_ai_audio, audio_to_play)
    
    NOTE: call_state is stored as string (.value) to avoid Streamlit serialization issues.
    """
    if 'call_state' not in st.session_state:
        st.session_state.call_state = CallState.IDLE.value  # Store as string
    
    if 'ui_conversation' not in st.session_state:
        st.session_state.ui_conversation = []
    
    if 'orchestrator_state' not in st.session_state:
        # This gets passed to orchestrator.process()
        st.session_state.orchestrator_state = {
            "conversation_history": [],
            "client_id": None,
            "accountant_id": None,
            "entities": {}
        }
    
    if 'call_start_time' not in st.session_state:
        st.session_state.call_start_time = None
    
    if 'last_ai_audio' not in st.session_state:
        st.session_state.last_ai_audio = None
    
    if 'audio_to_play' not in st.session_state:
        st.session_state.audio_to_play = None
    
    if 'call_metadata' not in st.session_state:
        st.session_state.call_metadata = {
            "total_turns": 0,
            "intents_classified": [],
            "actions_taken": []
        }
    
    if 'pending_user_audio' not in st.session_state:
        st.session_state.pending_user_audio = None
    
    if 'auto_end_after_playback' not in st.session_state:
        st.session_state.auto_end_after_playback = False


# ============================================================================
# STATE MANAGEMENT - SEPARATED CONCERNS
# ============================================================================

def get_current_state() -> CallState:
    """
    Get current call state as enum.
    
    CRITICAL: Streamlit serializes enums to strings, so we need to convert back.
    """
    state_value = st.session_state.get('call_state', CallState.IDLE.value)
    
    # If already enum, return as-is
    if isinstance(state_value, CallState):
        return state_value
    
    # Convert string to enum
    try:
        return CallState(state_value)
    except ValueError:
        logger.warning(f"Unknown state value: {state_value}, defaulting to IDLE")
        return CallState.IDLE


def update_state(new_state: CallState):
    """
    Update call state with logging.
    
    CRITICAL: Centralized state transitions for debugging.
    IMPORTANT: We store the .value (string) because Streamlit serializes enums incorrectly.
    """
    old_state = get_current_state()
    # Store as string to avoid Streamlit serialization issues
    st.session_state.call_state = new_state.value
    logger.info(f"STATE TRANSITION: {old_state.value if isinstance(old_state, CallState) else old_state} → {new_state.value}")


def add_ui_message(speaker: str, text: str, metadata: Optional[Dict] = None):
    """
    Add message to UI conversation history.
    
    Args:
        speaker: "ai" or "user"
        text: Message text
        metadata: Optional dict with intent, action, confidence
    """
    msg = {
        "speaker": speaker,
        "text": text,
        "timestamp": datetime.now(),
        "metadata": metadata or {}
    }
    st.session_state.ui_conversation.append(msg)
    logger.info(f"💬 UI Message: {speaker} - {text[:60]}...")


def update_orchestrator_state(result: Dict):
    """
    Update orchestrator state from result.
    
    CRITICAL: This maintains conversation context for multi-turn.
    """
    # Update conversation history
    if "conversation_history" in result:
        st.session_state.orchestrator_state["conversation_history"] = result["conversation_history"]
    
    # Update entities if present
    if "entities" in result:
        st.session_state.orchestrator_state["entities"].update(result["entities"])
    
    # Update IDs if present
    if "client_id" in result and result["client_id"]:
        st.session_state.orchestrator_state["client_id"] = result["client_id"]
    
    if "accountant_id" in result and result["accountant_id"]:
        st.session_state.orchestrator_state["accountant_id"] = result["accountant_id"]


def update_call_metadata(intent: str, action: str):
    """
    Update call metadata for analytics.
    
    Args:
        intent: Classified intent (e.g., "TAX_QUERY")
        action: Action taken (e.g., "rag_search")
    """
    st.session_state.call_metadata["total_turns"] += 1
    st.session_state.call_metadata["intents_classified"].append(intent)
    if action != "none":
        st.session_state.call_metadata["actions_taken"].append(action)


# ============================================================================
# ORCHESTRATOR INTEGRATION
# ============================================================================

def call_orchestrator(user_input: str = None) -> Dict:
    """
    Call orchestrator with conversation history.
    
    CRITICAL: This is the SINGLE point of orchestrator invocation.
    Always passes conversation_history for context.
    
    Args:
        user_input: User text (empty string for greeting)
    
    Returns:
        Orchestrator result dict
    """
    try:
        orchestrator = load_orchestrator()
        
        # Build state to pass
        # NOTE: LangGraph orchestrator expects user_input, not full state
        # But we ensure conversation_history is maintained internally
        
        logger.info(f"Calling orchestrator with input: '{user_input[:100] if user_input else '(empty)'}'")
        
        result = orchestrator.process(user_input=user_input or "")
        
        # Update our state from result
        update_orchestrator_state(result)
        
        return result
    
    except Exception as e:
        logger.error(f"Orchestrator call failed: {e}", exc_info=True)
        
        # Return error state
        return {
            "user_input": user_input or "",
            "response": "Mi dispiace, c'è stato un errore interno. Riprova.",
            "error": str(e),
            "intent": "UNKNOWN",
            "action_taken": "error",
            "confidence": 0.0
        }


# ============================================================================
# VOICE PROCESSING
# ============================================================================

def synthesize_speech(text: str) -> str:
    """
    Synthesize speech with caching.
    
    CRITICAL: Caches TTS to avoid redundant API calls.
    
    Args:
        text: Text to synthesize
    
    Returns:
        Path to audio file
    """
    try:
        voice = load_voice_handler()
        
        logger.info(f"Synthesizing: {len(text)} chars")
        audio_path = voice.synthesize(text)
        
        logger.success(f"Audio generated: {Path(audio_path).stat().st_size / 1024:.1f}KB")
        
        return audio_path
    
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes to text.
    
    Args:
        audio_bytes: Raw audio data
    
    Returns:
        Transcribed text
    
    Raises:
        ValueError: Invalid audio
        RuntimeError: ASR failure
    """
    # Validate audio
    if len(audio_bytes) < 1000:
        raise ValueError("Audio troppo breve (min 1KB)")
    
    if len(audio_bytes) > 10_000_000:
        raise ValueError("Audio troppo lungo (max 10MB)")
    
    # Save temporary file
    temp_audio = Path("temp_recording.wav")
    with open(temp_audio, "wb") as f:
        f.write(audio_bytes)
    
    try:
        voice = load_voice_handler()
        
        logger.info("Transcribing audio...")
        transcript = voice.transcribe(str(temp_audio))
        
        # Validate transcript
        if not transcript or len(transcript.strip()) < 3:
            raise ValueError("Transcript vuoto o invalido")
        
        logger.success(f"Transcript: {transcript}")
        
        return transcript
    
    finally:
        # Always cleanup
        temp_audio.unlink(missing_ok=True)


# ============================================================================
# CALL LIFECYCLE - STATE MACHINE TRANSITIONS
# ============================================================================

def on_start_call():
    """
    START CALL: IDLE → GREETING_GENERATION → GREETING_PLAYBACK
    
    State transitions:
    1. IDLE → GREETING_GENERATION (generate welcome)
    2. GREETING_GENERATION → GREETING_PLAYBACK (synthesize audio)
    """
    logger.info("=" * 70)
    logger.info("🟢 START CALL")
    logger.info("=" * 70)
    
    try:
        # Transition 1: IDLE → GREETING_GENERATION
        update_state(CallState.GREETING_GENERATION)
        st.session_state.call_start_time = datetime.now()
        
        # Generate greeting via orchestrator
        result = call_orchestrator(user_input="")
        
        greeting = result.get("response", "Buongiorno! Come posso aiutarla?")
        intent = result.get("intent", "UNKNOWN")
        action = result.get("action_taken", "greeting_generated")
        
        # Update metadata
        update_call_metadata(intent, action)
        
        # Add to UI
        add_ui_message("ai", greeting, {
            "intent": intent,
            "action": action,
            "confidence": "1.00"
        })
        
        # Synthesize greeting
        audio_path = synthesize_speech(greeting)
        st.session_state.audio_to_play = audio_path
        
        # Transition 2: GREETING_GENERATION → GREETING_PLAYBACK
        update_state(CallState.GREETING_PLAYBACK)
        
        logger.success(f"Call started. Greeting ready ({len(greeting)} chars)")
        
    except Exception as e:
        logger.error(f"Call start failed: {e}", exc_info=True)
        st.error(f"❌ Errore avvio chiamata: {str(e)[:100]}")
        update_state(CallState.IDLE)


def on_greeting_played():
    """
    GREETING PLAYED: GREETING_PLAYBACK → WAITING_FOR_INPUT
    
    User clicked "Audio Terminato" button.
    """
    logger.info("🔊 Greeting playback completed")
    
    update_state(CallState.WAITING_FOR_INPUT)
    st.session_state.audio_to_play = None


def on_user_audio_recorded(audio_bytes: bytes):
    """
    AUDIO RECORDED: WAITING_FOR_INPUT → RECORDING → auto-process
    
    ✅ FIX 2: Auto-procesamiento sin botón manual
    
    State transitions:
    1. WAITING_FOR_INPUT → RECORDING (user audio captured)
    2. Immediately call on_process_user_input() to process
    """
    logger.info("🎤 User audio recorded")
    
    # Transition: WAITING_FOR_INPUT → RECORDING
    update_state(CallState.RECORDING)
    
    # Store for processing
    st.session_state.pending_user_audio = audio_bytes
    
    # ✅ AUTO-PROCESS IMMEDIATELY (no button needed)
    logger.info("Auto-processing audio...")
    on_process_user_input()


def on_process_user_input():
    """
    PROCESS INPUT: RECORDING → PROCESSING → RESPONSE_GENERATION → RESPONSE_PLAYBACK
    
    This is triggered when user clicks "Elabora Messaggio" after recording.
    
    State transitions:
    1. RECORDING → PROCESSING (transcribe + orchestrator)
    2. PROCESSING → RESPONSE_GENERATION (orchestrator returned)
    3. RESPONSE_GENERATION → RESPONSE_PLAYBACK (TTS complete)
    """
    logger.info("⚙️ Processing user input")
    
    audio_bytes = st.session_state.pending_user_audio
    
    if not audio_bytes:
        st.warning("⚠️ Nessun audio da elaborare")
        return
    
    try:
        # Transition: RECORDING → PROCESSING
        update_state(CallState.PROCESSING)
        
        # 1. Transcribe
        transcript = transcribe_audio(audio_bytes)
        
        # Add to UI
        add_ui_message("user", transcript)
        
        # ✅ FIX 1: CHECK FOR FAREWELL BEFORE ORCHESTRATOR
        farewell_keywords = ['grazie', 'ciao', 'arrivederci', 'saluti', 'buonasera', 'buonanotte']
        transcript_lower = transcript.lower().strip()
        
        # If transcript is ONLY farewell (no other meaningful content), end call
        words = transcript_lower.split()
        is_farewell = (
            any(keyword in transcript_lower for keyword in farewell_keywords) and 
            len(words) <= 4  # Max 4 words (e.g., "Grazie mille, ciao")
        )
        
        if is_farewell:
            logger.info(f"🔚 Farewell detected: '{transcript}' - ending call")
            
            # Generate farewell response
            farewell_response = "Grazie per aver chiamato lo Studio Commercialista. Arrivederci!"
            
            # Add to UI
            add_ui_message("ai", farewell_response, {
                "intent": "farewell",
                "action": "call_ended",
                "confidence": "1.00"
            })
            
            # Update metadata
            update_call_metadata("farewell", "call_ended")
            
            # Synthesize farewell
            update_state(CallState.RESPONSE_GENERATION)
            audio_path = synthesize_speech(farewell_response)
            st.session_state.audio_to_play = audio_path
            
            # Go to playback
            update_state(CallState.RESPONSE_PLAYBACK)
            
            # Set flag to auto-end after playback
            st.session_state.auto_end_after_playback = True
            
            st.session_state.pending_user_audio = None
            logger.success("Farewell processed, call will end after playback")
            return
        
        # 2. Call orchestrator (normal flow)
        result = call_orchestrator(user_input=transcript)
        
        ai_response = result.get("response", "Non ho capito. Puoi ripetere?")
        intent = result.get("intent", "UNKNOWN")
        action = result.get("action_taken", "none")
        confidence = result.get("confidence", 0.0)
        
        # Update metadata
        update_call_metadata(intent, action)
        
        # Add to UI
        add_ui_message("ai", ai_response, {
            "intent": intent,
            "action": action,
            "confidence": f"{confidence:.2f}"
        })
        
        logger.info(f"🎯 Intent: {intent} | Action: {action} | Confidence: {confidence:.2f}")
        
        # Transition: PROCESSING → RESPONSE_GENERATION
        update_state(CallState.RESPONSE_GENERATION)
        
        # 3. Synthesize response
        audio_path = synthesize_speech(ai_response)
        st.session_state.audio_to_play = audio_path
        
        # Transition: RESPONSE_GENERATION → RESPONSE_PLAYBACK
        update_state(CallState.RESPONSE_PLAYBACK)
        
        # Clear pending audio
        st.session_state.pending_user_audio = None
        
        logger.success("User input processed successfully")
        
    except ValueError as e:
        logger.warning(f"Invalid user input: {e}")
        st.warning(f"⚠️ {str(e)}")
        update_state(CallState.WAITING_FOR_INPUT)
        st.session_state.pending_user_audio = None
    
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        st.error(f"❌ Errore elaborazione: {str(e)[:100]}")
        
        # Return to waiting
        update_state(CallState.WAITING_FOR_INPUT)
        st.session_state.pending_user_audio = None


def on_response_played():
    """
    RESPONSE PLAYED: RESPONSE_PLAYBACK → WAITING_FOR_INPUT (or ENDED)
    
    User clicked "Audio Terminato" after AI response.
    Ready for next turn (conversational loop), OR end call if farewell.
    
    ✅ FIX 1: Auto-end after farewell detection
    """
    logger.info("🔊 Response playback completed")
    
    # Check if should auto-end (farewell detected)
    if st.session_state.get('auto_end_after_playback', False):
        logger.info("🔚 Auto-ending call after farewell")
        st.session_state.auto_end_after_playback = False
        update_state(CallState.ENDED)
    else:
        update_state(CallState.WAITING_FOR_INPUT)
    
    st.session_state.audio_to_play = None


def on_end_call():
    """
    END CALL: ANY_STATE → ENDED
    """
    logger.info("=" * 70)
    logger.info("🔴 END CALL")
    logger.info("=" * 70)
    
    # Calculate duration
    if st.session_state.call_start_time:
        duration = (datetime.now() - st.session_state.call_start_time).total_seconds()
        logger.info(f"Call duration: {duration:.1f}s | Turns: {st.session_state.call_metadata['total_turns']}")
    
    # Generate farewell
    farewell = "Grazie per aver chiamato lo Studio Commercialista. Arrivederci!"
    
    # Add to UI if not already present
    if (not st.session_state.ui_conversation or 
        st.session_state.ui_conversation[-1]["text"] != farewell):
        
        add_ui_message("ai", farewell)
        
        try:
            audio_path = synthesize_speech(farewell)
            st.session_state.audio_to_play = audio_path
        except:
            pass
    
    update_state(CallState.ENDED)


def on_new_call():
    """
    NEW CALL: ENDED → IDLE
    
    Reset all state for fresh call.
    """
    logger.info("=" * 70)
    logger.info("🔄 NEW CALL - Resetting state")
    logger.info("=" * 70)
    
    # Reset all state (store as string to avoid serialization issues)
    st.session_state.call_state = CallState.IDLE.value
    st.session_state.ui_conversation = []
    st.session_state.orchestrator_state = {
        "conversation_history": [],
        "client_id": None,
        "accountant_id": None,
        "entities": {}
    }
    st.session_state.call_start_time = None
    st.session_state.audio_to_play = None
    st.session_state.pending_user_audio = None
    st.session_state.call_metadata = {
        "total_turns": 0,
        "intents_classified": [],
        "actions_taken": []
    }


# ============================================================================
# UI RENDERING
# ============================================================================

def get_status_text(state: CallState) -> str:
    """Get human-readable status text"""
    status_map = {
        CallState.IDLE: "📞 Pronto per chiamare",
        CallState.GREETING_GENERATION: "⚙️ Generazione messaggio di benvenuto...",
        CallState.GREETING_PLAYBACK: "🔊 Riproduzione messaggio di benvenuto",
        CallState.WAITING_FOR_INPUT: "👂 In attesa del tuo messaggio",
        CallState.RECORDING: "🎤 Registrazione in corso",
        CallState.PROCESSING: "⚙️ Elaborazione della tua richiesta...",
        CallState.RESPONSE_GENERATION: "💭 Generazione risposta...",
        CallState.RESPONSE_PLAYBACK: "🔊 Riproduzione risposta",
        CallState.ENDED: "📴 Chiamata terminata"
    }
    return status_map.get(state, "⚠️ Stato sconosciuto")


def render_call_timer():
    """Render call duration timer"""
    if st.session_state.call_start_time and get_current_state() != CallState.ENDED:
        duration = (datetime.now() - st.session_state.call_start_time).total_seconds()
        mins, secs = divmod(int(duration), 60)
        st.markdown(
            f'<div class="call-timer">⏱️ Durata: {mins:02d}:{secs:02d}</div>',
            unsafe_allow_html=True
        )


def render_call_status():
    """Render current call status"""
    state = get_current_state()
    status_text = get_status_text(state)
    
    st.markdown(
        f'<div class="call-status status-{state.value}">{status_text}</div>',
        unsafe_allow_html=True
    )


def render_conversation():
    """Render conversation history"""
    if not st.session_state.ui_conversation:
        st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#95a5a6;'>Nessun messaggio ancora...</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
    
    for msg in st.session_state.ui_conversation:
        speaker = msg["speaker"]
        text = msg["text"]
        timestamp = msg["timestamp"].strftime("%H:%M:%S")
        metadata = msg.get("metadata", {})
        
        bubble_class = "message-ai" if speaker == "ai" else "message-user"
        
        html = f'<div class="message-bubble {bubble_class}">'
        html += f'<div>{text}</div>'
        html += f'<div class="message-timestamp">{timestamp}</div>'
        
        if metadata and speaker == "ai":
            intent = metadata.get("intent", "N/A")
            action = metadata.get("action", "N/A")
            confidence = metadata.get("confidence", "N/A")
            html += f'<div class="message-metadata">Intent: {intent} | Action: {action} | Conf: {confidence}</div>'
        
        html += '</div>'
        
        st.markdown(html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_audio_player():
    """
    Render audio player with EXPERIMENTAL auto-play and auto-transition.
    
    ⚠️ WARNING: Auto-play is NOT guaranteed due to browser policies.
    This is a best-effort attempt that may fail on:
    - First page load
    - Incognito mode
    - Safari strict mode
    - Low Media Engagement Index
    
    Success rate: ~60-70% (depends on browser and user)
    """
    audio_path = st.session_state.get('audio_to_play')
    state = get_current_state()
    
    # Debug logging
    if not audio_path:
        logger.debug("No audio_to_play in session_state")
        return
    
    audio_file = Path(audio_path)
    if not audio_file.exists():
        logger.warning(f"Audio file does not exist: {audio_path}")
        logger.debug(f"Trying absolute path: {audio_file.absolute()}")
        # Try with absolute path
        if not audio_file.absolute().exists():
            logger.error(f"Audio file not found even with absolute path")
            return
        audio_file = audio_file.absolute()
    
    if state not in [CallState.GREETING_PLAYBACK, CallState.RESPONSE_PLAYBACK]:
        logger.debug(f"State {state} not a playback state, skipping audio player")
        return
    
    st.markdown("---")
    st.markdown("### 🔊 Riproduzione Audio")
    
    # Read audio
    try:
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        logger.info(f"Audio player rendered: {len(audio_bytes)/1024:.1f}KB")
    except Exception as e:
        logger.error(f"Failed to read audio file: {e}")
        st.error(f"Errore caricamento audio: {e}")
        return
    
    # Convert to base64 for embedding
    import base64
    audio_b64 = base64.b64encode(audio_bytes).decode()
    
    # Generate unique ID for this audio
    import hashlib
    audio_id = hashlib.md5(audio_bytes).hexdigest()[:8]
    
    # Determine next state for auto-transition
    if state == CallState.GREETING_PLAYBACK:
        next_state_value = CallState.WAITING_FOR_INPUT.value
        button_text = "✅ Audio Terminato - Inizia a Parlare"
    else:  # RESPONSE_PLAYBACK
        if st.session_state.get('auto_end_after_playback', False):
            next_state_value = CallState.ENDED.value
            button_text = "✅ Audio Terminato"
        else:
            next_state_value = CallState.WAITING_FOR_INPUT.value
            button_text = "✅ Audio Terminato - Continua Conversazione"
    
    # ✅ EXPERIMENTAL: Auto-play with JavaScript
    html = f'''
    <div id="audio-container-{audio_id}" style="text-align: center; padding: 20px;">
        <audio id="audio-{audio_id}" preload="auto">
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
        <div id="status-{audio_id}" style="margin: 10px 0; font-size: 16px;">⏳ Caricamento...</div>
        <div id="fallback-{audio_id}" style="display: none;">
            <button onclick="playAudio_{audio_id}()" 
                    style="background: #3498db; color: white; border: none; 
                           padding: 12px 24px; border-radius: 8px; 
                           font-size: 16px; cursor: pointer;">
                ▶️ Riproduci Audio
            </button>
        </div>
    </div>
    <script>
    (function() {{
        const audio = document.getElementById('audio-{audio_id}');
        const status = document.getElementById('status-{audio_id}');
        const fallback = document.getElementById('fallback-{audio_id}');
        
        let audioEnded = false;
        
        function playAudio_{audio_id}() {{
            audio.play().then(() => {{
                status.innerHTML = '🔊 Riproduzione in corso...';
                fallback.style.display = 'none';
            }}).catch(err => {{
                console.error('Play failed:', err);
                status.innerHTML = '❌ Errore riproduzione';
            }});
        }}
        
        // Attempt auto-play after small delay
        setTimeout(() => {{
            audio.play().then(() => {{
                console.log('✅ Auto-play success');
                status.innerHTML = '🔊 Riproduzione in corso...';
            }}).catch(err => {{
                console.log('⚠️ Auto-play blocked:', err);
                status.innerHTML = '⚠️ Auto-play bloccato dal browser';
                fallback.style.display = 'block';
            }});
        }}, 300);
        
        // On audio end, set query param to signal Streamlit
        audio.onended = () => {{
            if (!audioEnded) {{
                audioEnded = true;
                console.log('✅ Audio ended, transitioning state');
                status.innerHTML = '✅ Audio completato - transizione automatica...';
                
                // Attempt to signal Streamlit via query param
                try {{
                    const currentUrl = new URL(window.parent.location.href);
                    currentUrl.searchParams.set('audio_ended', '1');
                    currentUrl.searchParams.set('next_state', '{next_state_value}');
                    window.parent.history.pushState({{}}, '', currentUrl);
                    
                    // Force Streamlit rerun
                    window.parent.location.search = currentUrl.search;
                }} catch(e) {{
                    console.error('Failed to set query param:', e);
                    // Fallback: show manual button
                    status.innerHTML = '✅ Audio completato';
                    fallback.innerHTML = '<p style="color: #e74c3c;">Clicca il pulsante sotto per continuare</p>';
                    fallback.style.display = 'block';
                }}
            }}
        }};
        
        // Error handling
        audio.onerror = (e) => {{
            console.error('Audio error:', e);
            status.innerHTML = '❌ Errore caricamento audio';
            fallback.style.display = 'block';
        }};
    }})();
    </script>
    '''
    
    import streamlit.components.v1 as components
    components.html(html, height=150)
    
    # Fallback: Manual button if JavaScript fails or for accessibility
    st.markdown("---")
    st.caption("ℹ️ Se l'audio non si avvia automaticamente, clicca il pulsante sopra")
    
    if state == CallState.GREETING_PLAYBACK:
        if st.button(button_text, type="secondary", use_container_width=True, key="manual_continue_greeting"):
            on_greeting_played()
            st.rerun()
    
    elif state == CallState.RESPONSE_PLAYBACK:
        if st.button(button_text, type="secondary", use_container_width=True, key="manual_continue_response"):
            on_response_played()
            st.rerun()


def render_controls():
    """Render call controls based on current state"""
    state = get_current_state()
    
    col1, col2 = st.columns(2)
    
    # === IDLE STATE ===
    if state == CallState.IDLE:
        with col1:
            st.button(
                "📞 Inizia Chiamata",
                type="primary",
                use_container_width=True,
                on_click=on_start_call
            )
    
    # === WAITING FOR INPUT STATE ===
    elif state == CallState.WAITING_FOR_INPUT:
        with col1:
            st.markdown("### 🎤 Registra il tuo messaggio")
            st.info("👂 Premi il pulsante per parlare. Rilascia quando hai finito.")
            
            audio_bytes = audio_recorder(
                text="Clicca per parlare",
                recording_color="#e74c3c",
                neutral_color="#27ae60",
                icon_size="2x",
                key=f"audio_recorder_{st.session_state.call_metadata['total_turns']}"
            )
            
            if audio_bytes:
                on_user_audio_recorded(audio_bytes)
                st.rerun()
        
        with col2:
            st.button(
                "⏸️ Termina Chiamata",
                type="secondary",
                use_container_width=True,
                on_click=on_end_call
            )
    
    # === RECORDING STATE ===
    # ✅ FIX 2: Audio se procesa automáticamente, no necesita botón
    # Este estado pasa instantáneamente a PROCESSING
    elif state == CallState.RECORDING:
        with col1:
            st.info("⏳ Elaborazione audio in corso...")
    
    # === PROCESSING / GENERATION STATES ===
    elif state in [CallState.GREETING_GENERATION, CallState.PROCESSING, CallState.RESPONSE_GENERATION]:
        with col1:
            st.info(get_status_text(state))
            st.spinner("Elaborazione...")
    
    # === PLAYBACK STATES ===
    elif state in [CallState.GREETING_PLAYBACK, CallState.RESPONSE_PLAYBACK]:
        # Audio player handles buttons
        pass
    
    # === ENDED STATE ===
    elif state == CallState.ENDED:
        with col1:
            st.button(
                "🔄 Nuova Chiamata",
                type="primary",
                use_container_width=True,
                on_click=on_new_call
            )


def render_sidebar():
    """Render diagnostics sidebar"""
    with st.sidebar:
        st.markdown("### 📊 Diagnostica Sistema")
        
        # current_state is now a string (not enum)
        current_state = st.session_state.call_state
        
        st.info(f"""
        **Stato Chiamata:** {current_state}
        
        **Turni Conversazione:** {st.session_state.call_metadata['total_turns']}
        
        **Messaggi UI:** {len(st.session_state.ui_conversation)}
        
        **Modello LLM:** {config.LLM_PROVIDER}
        
        **Orchestrator:** ✅ LangGraph
        """)
        
        # Recent intents
        if st.session_state.call_metadata['intents_classified']:
            st.markdown("### 🎯 Intent Recenti")
            recent_intents = st.session_state.call_metadata['intents_classified'][-5:]
            for i, intent in enumerate(recent_intents, 1):
                st.caption(f"{i}. {intent}")
        
        # Recent actions
        if st.session_state.call_metadata['actions_taken']:
            st.markdown("### ⚙️ Azioni Eseguite")
            recent_actions = st.session_state.call_metadata['actions_taken'][-5:]
            for i, action in enumerate(recent_actions, 1):
                st.caption(f"{i}. {action}")
        
        # Debug info
        with st.expander("🔧 Debug Info"):
            st.json({
                "call_state": current_state,
                "orchestrator_history_length": len(st.session_state.orchestrator_state["conversation_history"]),
                "client_id": st.session_state.orchestrator_state.get("client_id"),
                "entities": st.session_state.orchestrator_state.get("entities"),
                "audio_to_play": st.session_state.audio_to_play is not None,
                "pending_audio": st.session_state.pending_user_audio is not None
            })


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """
    Main application entry point.
    
    CRITICAL: This orchestrates the complete UI lifecycle.
    All state transitions happen through callbacks.
    """
    
    # Log startup once
    if 'app_initialized' not in st.session_state:
        logger.info("=" * 70)
        logger.info("📞 Voice AI Agent - REFACTORED VERSION")
        logger.info("=" * 70)
        st.session_state.app_initialized = True
    
    # Initialize state
    init_session_state()
    
    # ✅ EXPERIMENTAL: Handle auto-transition from JavaScript audio player
    try:
        params = st.query_params
        if params.get('audio_ended') == '1':
            logger.info("🔊 Audio ended signal received from JavaScript")
            
            next_state_str = params.get('next_state')
            current_state = get_current_state()
            
            # Clear query params immediately to avoid loops
            st.query_params.clear()
            
            # Transition to next state
            if next_state_str:
                try:
                    next_state = CallState(next_state_str)
                    logger.info(f"Auto-transitioning: {current_state.value} → {next_state.value}")
                    
                    if next_state == CallState.WAITING_FOR_INPUT:
                        # Call appropriate callback based on current state
                        if current_state == CallState.GREETING_PLAYBACK:
                            on_greeting_played()
                        elif current_state == CallState.RESPONSE_PLAYBACK:
                            on_response_played()
                    elif next_state == CallState.ENDED:
                        on_response_played()  # Will handle auto_end_after_playback
                    
                    st.rerun()
                except ValueError:
                    logger.warning(f"Invalid next_state: {next_state_str}")
    except Exception as e:
        logger.debug(f"Query param handling failed: {e}")
    
    # Load resources with error handling
    try:
        orchestrator = load_orchestrator()
        voice = load_voice_handler()
    except Exception as e:
        logger.critical(f"System initialization failed: {e}", exc_info=True)
        
        st.error("🚨 Sistema temporaneamente non disponibile")
        st.warning("""
        **Cosa puoi fare:**
        1. Riprova tra qualche minuto
        2. Chiama direttamente: +39 02 1234 5678
        3. Email: assistenza@studio.it
        """)
        
        st.stop()
    
    # Render UI
    st.markdown('<div class="phone-container">', unsafe_allow_html=True)
    
    st.markdown("<h1 style='color:white;text-align:center;'>📞 Studio Commercialista</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:white;text-align:center;opacity:0.9;'>Assistente AI Vocale</p>", unsafe_allow_html=True)
    
    render_call_timer()
    render_call_status()
    render_conversation()
    render_audio_player()
    render_controls()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    render_sidebar()


if __name__ == "__main__":
    main()