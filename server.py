"""
Twilio Voice Server - Voice AI Agent MVP
Integrates existing orchestrator, RAG engine, and database
"""
from urllib import response
from flask import Flask, Response, request, session
from twilio.twiml.voice_response import VoiceResponse, Gather, Say
from twilio.rest import Client
from loguru import logger
import os
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict
import json
import re

# Import your existing code
from orchestrator import Orchestrator
from rag_engine import RAGEngine
import config

# Load environment variables
load_dotenv()

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')


@app.before_request
def _log_incoming_requests():
    """Lightweight request logging for Twilio webhooks (helps diagnose missing /voice/incoming hits)."""
    if request.path.startswith("/voice"):
        call_sid = request.values.get("CallSid") or request.args.get("CallSid")
        logger.info(f"➡️  {request.method} {request.path} CallSid={call_sid or 'n/a'}")

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# ============================================================================
# PRE-INITIALIZE HEAVY COMPONENTS
# ============================================================================
# CRITICAL: Initialize these ONCE at startup, not per-request
# This prevents 7-15s delays during calls

logger.info("Pre-initializing RAG Engine...")
rag_engine = RAGEngine()
logger.success(f"RAG Engine ready with {rag_engine.collection.count()} chunks")

logger.info("Initializing Orchestrator...")
orchestrator = Orchestrator()
logger.success("Orchestrator ready")

# Session storage (in-memory for MVP, use Redis for production)
# Note: Orchestrator maintains conversation state internally
call_sessions = defaultdict(lambda: {
    "turn_count": 0,
    "start_time": None,
    # Persist orchestrator context per call to keep a coherent multi-turn thread
    "context": {},
    "call_metadata": {
        "intents": [],
        "actions": []
    }
})

# ============================================================================
# CONFIGURATION
# ============================================================================

VOICE_CONFIG = {
    "language": "it-IT",
    "voice": "Google.it-IT-Wavenet-C",  # Twilio's Italian voice
    "speech_timeout": "auto",  # Auto-detect when user stops speaking
    "max_speech_time": 30,  # Max 30 seconds per utterance
    # Hints help STT on short replies (e.g., times like "13" / "tredici").
    "hints": (
        "appuntamento, prenotare, disponibilità, orario, giorno, domani, oggi, dopodomani, "
        "9, 10, 11, 12, 13, 14, 15, 16, 17, 18, "
        "nove, dieci, undici, dodici, tredici, quattordici, quindici, sedici, diciassette, diciotto, "
        "alle 9, alle 10, alle 11, alle 12, alle 13, alle 14, alle 15, alle 16, alle 17, "
        "tredici e trenta, tredici e un quarto"
    )
}

# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.route("/voice/incoming", methods=["GET", "POST"])
def incoming_call():
    """
    Maneja llamadas entrantes.
    Solo envía saludo inicial - NO procesa input todavía.
    """
    call_sid = request.values.get("CallSid", "unknown")
    from_number = request.values.get("From", "unknown")
    to_number = request.values.get("To", "unknown")
    
    logger.info("=" * 70)
    logger.info(f"📞 INCOMING CALL: {call_sid}")
    logger.info(f"From: {from_number} → To: {to_number}")
    logger.info("=" * 70)

    # Ensure per-call session is initialized
    session_data = call_sessions[call_sid]
    if session_data.get("start_time") is None:
        session_data["start_time"] = datetime.now()

    # Store caller phone for later turns (orchestrator can use it for client lookup)
    session_data.setdefault("context", {})
    session_data["context"].setdefault("client_phone", from_number)
    
    # ✅ CORRECTO: Solo enviamos saludo, NO llamamos orchestrator
    response = VoiceResponse()
    
    # Saluto iniziale (breve, naturale, senza riferimenti a "AI")
    response.say(
        "Buongiorno, Studio Commercialista. In cosa posso esserLe utile?",
        language="it-IT",
        voice="Google.it-IT-Wavenet-C"
    )
    
    # Gather con configuración optimizada
    gather = Gather(
        input="speech",
        language="it-IT",
        action="/voice/gather",
        speech_timeout="auto",
        speech_model="phone_call",
        # Hints tuned for scheduling + short numeric replies
        hints=VOICE_CONFIG["hints"],
        bargeIn=True,  # Permite interrumpir
        enhanced=True  # Usa modelo ASR mejorado
    )
    
    response.append(gather)
    
    # Fallback se non arriva input
    response.say(
        "Non ho ricevuto risposta. Può richiamare quando desidera. Arrivederci.",
        language="it-IT",
        voice="Google.it-IT-Wavenet-C"
    )
    response.hangup()
    
    logger.info("📤 Sending TwiML response")
    
    return Response(str(response), mimetype="text/xml")


# Accept trailing slash too (Twilio console sometimes ends up with /)
@app.route("/voice/incoming/", methods=["GET", "POST"])
def incoming_call_slash():
    return incoming_call()

@app.route("/voice/gather", methods=['POST'])
def gather_speech():
    """
    Twilio calls this endpoint after user speaks.
    
    This processes the user's input and generates a response.
    """
    call_sid = request.values.get('CallSid')
    from_number = request.values.get('From', 'unknown')
    transcript = request.values.get('SpeechResult', '').strip()
    confidence = request.values.get('Confidence', '0.0')

    try:
        confidence_val = float(confidence)
    except Exception:
        confidence_val = 0.0
    
    logger.info("=" * 70)
    logger.info(f"🎤 USER INPUT: {call_sid}")
    logger.info(f"Transcript: '{transcript}' (confidence: {confidence})")
    logger.info("=" * 70)
    
    # Get session
    session_data = call_sessions[call_sid]
    if session_data.get("start_time") is None:
        # Defensive: start_time should be set in /voice/incoming, but ensure it's present
        session_data["start_time"] = datetime.now()
    session_data["turn_count"] += 1
    
    response = VoiceResponse()

    # If we are in a slot-filling follow-up (e.g., asking for time) and STT confidence is low,
    # avoid sending a likely-wrong transcript into the orchestrator (which then re-asks and feels like a loop).
    prior_context = session_data.get("context") or {}
    expected_slot = (prior_context.get("entities") or {}).get("expected_slot")
    transcript_lower = transcript.lower()
    if expected_slot in {"time", "date", "date_time"} and confidence_val > 0.0 and confidence_val < 0.55:
        has_digits = bool(re.search(r"\d", transcript))
        has_date_word = any(w in transcript_lower for w in ("oggi", "domani", "dopodomani"))
        if not has_digits and not has_date_word:
            logger.warning(
                f"⚠️ Low-confidence follow-up for slot={expected_slot}: '{transcript}' ({confidence_val:.3f})"
            )
            response.say(
                "Mi scusi, non ho capito bene. Mi può dire giorno e orario in modo semplice, per esempio 'domani alle 13' o 'giovedì alle 15'?",
                **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
            )
            gather = Gather(
                input='speech',
                language=VOICE_CONFIG['language'],
                speech_timeout=VOICE_CONFIG['speech_timeout'],
                max_speech_time=VOICE_CONFIG['max_speech_time'],
                hints=VOICE_CONFIG['hints'],
                speech_model="phone_call",
                bargeIn=True,
                enhanced=True,
                action='/voice/gather',
                method='POST'
            )
            response.append(gather)
            return Response(str(response), mimetype="text/xml")

    # Guard: sometimes STT returns only filler like "alle" with high confidence.
    # Treat it as non-informative when we are explicitly expecting a time/date.
    if expected_slot in {"time", "date", "date_time"}:
        filler_only = {
            "alle", "a", "allora", "eh", "e", "ok", "okay", "si", "sì",
        }
        if transcript_lower.strip() in filler_only:
            logger.warning(
                f"⚠️ Non-informative follow-up for slot={expected_slot}: '{transcript}' ({confidence_val:.3f})"
            )
            if expected_slot == "time":
                prompt = "Mi scusi, ho sentito solo 'alle'. Mi può dire un orario, per esempio 'alle 13' o 'alle 15 e 30'?"
            elif expected_slot == "date":
                prompt = "Mi scusi, non ho colto il giorno. Mi può dire 'oggi', 'domani' oppure un giorno della settimana?"
            else:
                prompt = "Mi scusi, non ho colto giorno e orario. Per esempio: 'domani alle 13'."

            response.say(
                prompt,
                **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
            )
            gather = Gather(
                input='speech',
                language=VOICE_CONFIG['language'],
                speech_timeout=VOICE_CONFIG['speech_timeout'],
                max_speech_time=VOICE_CONFIG['max_speech_time'],
                hints=VOICE_CONFIG['hints'],
                speech_model="phone_call",
                bargeIn=True,
                enhanced=True,
                action='/voice/gather',
                method='POST'
            )
            response.append(gather)
            return Response(str(response), mimetype="text/xml")
    
    # Handle empty input (but allow short valid answers like "13")
    if not transcript or not re.search(r"[A-Za-zÀ-ÿ0-9]", transcript):
        logger.warning("⚠️ Empty or very short input")
        response.say(
            "Non ho sentito nulla. Può ripetere, per favore?",
            **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
        )
        
        # Try again
        gather = Gather(
            input='speech',
            language=VOICE_CONFIG['language'],
            speech_timeout=VOICE_CONFIG['speech_timeout'],
            max_speech_time=VOICE_CONFIG['max_speech_time'],
            hints=VOICE_CONFIG['hints'],
            speech_model="phone_call",
            bargeIn=True,
            enhanced=True,
            action='/voice/gather',
            method='POST'
        )
        response.append(gather)
        return Response(str(response), mimetype="text/xml")
    
    # Check for farewell
    farewell_keywords = ['grazie', 'ciao', 'arrivederci', 'saluti', 'buonasera', 'buonanotte', 'va bene']
    transcript_lower = transcript.lower()
    
    is_farewell = (
        any(keyword in transcript_lower for keyword in farewell_keywords) and
        len(transcript.split()) <= 4
    )
    
    if is_farewell:
        logger.info(f"🔚 Farewell detected: '{transcript}'")
        
        # Calculate call duration
        start_time = session_data.get("start_time")
        duration = None
        if isinstance(start_time, datetime):
            duration = (datetime.now() - start_time).total_seconds()

        if duration is not None:
            logger.info(f"📊 Call stats: {session_data['turn_count']} turns, {duration:.1f}s")
        else:
            logger.info(f"📊 Call stats: {session_data['turn_count']} turns")
        
        response.say(
            "Grazie per aver chiamato lo Studio Commercialista. Arrivederci!",
            **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
        )
        response.hangup()
        
        # Clean up session
        del call_sessions[call_sid]
        
        return Response(str(response), mimetype="text/xml")
    
    # Process with orchestrator
    try:
        logger.info("⚙️ Processing with orchestrator...")

        # ✅ Multi-turn continuity: pass back context from previous turn
        # This avoids "resetting" the conversation and re-listing capabilities.
        prior_context = session_data.get("context") or {}
        # Ensure caller phone is present for any caller identification logic
        prior_context.setdefault("client_phone", request.values.get("From") or request.values.get("Caller") or from_number)

        result = orchestrator.process(user_input=transcript, context=prior_context)

        # Persist context for next turn
        session_data["context"] = result.get("context") or prior_context
        
        # Get response
        intent = result.get("intent", "unknown")
        action = result.get("action_taken", "none")
        
        # Track metadata in session
        session_data["call_metadata"]["intents"].append(intent)
        session_data["call_metadata"]["actions"].append(action)
        
        ai_response = result.get("response", "Mi scusi, non ho capito. Può ripetere, per favore?")
        
        logger.success(f"✅ Orchestrator response: {len(ai_response)} chars")
        logger.info(f"🎯 Intent: {intent} | Action: {action}")
        
    except Exception as e:
        logger.error(f"❌ Orchestrator error: {e}", exc_info=True)
        ai_response = "Mi scusi, si è verificato un problema tecnico. Può riprovare?"
    
    # Build response
    response.say(
        ai_response,
        **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
    )
    
    # Continue conversation loop
    gather = Gather(
        input='speech',
        language=VOICE_CONFIG['language'],
        speech_timeout=VOICE_CONFIG['speech_timeout'],
        max_speech_time=VOICE_CONFIG['max_speech_time'],
        hints=VOICE_CONFIG['hints'],
        speech_model="phone_call",
        bargeIn=True,
        enhanced=True,
        action='/voice/gather',
        method='POST'
    )
    response.append(gather)
    
    # If no input, redirect
    response.redirect('/voice/gather')
    
    logger.info("📤 Sending TwiML response with gather")

    return Response(str(response), mimetype="text/xml")


# Accept trailing slash too
@app.route("/voice/gather/", methods=['POST'])
def gather_speech_slash():
    return gather_speech()


@app.route("/voice/status", methods=['POST'])
def call_status():
    """
    Twilio calls this endpoint for call status updates.
    
    Useful for logging and analytics.
    """
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    call_duration = request.values.get('CallDuration', '0')
    
    logger.info(f"📊 Call Status Update: {call_sid}")
    logger.info(f"   Status: {call_status}")
    logger.info(f"   Duration: {call_duration}s")
    
    if call_status == 'completed':
        # Clean up session if still exists
        if call_sid in call_sessions:
            session_data = call_sessions[call_sid]
            logger.info(f"   Turns: {session_data['turn_count']}")
            logger.info(f"   Intents: {session_data['call_metadata']['intents']}")
            del call_sessions[call_sid]
    
    return '', 200


@app.route("/voice/status/", methods=['POST'])
def call_status_slash():
    return call_status()


@app.route("/voice/fallback", methods=['POST'])
def fallback():
    """
    Twilio calls this if main webhook fails.
    
    Provides graceful error handling.
    """
    call_sid = request.values.get('CallSid')
    logger.error(f"❌ FALLBACK triggered for call: {call_sid}")
    
    response = VoiceResponse()
    response.say(
        "Mi scusi, stiamo avendo problemi tecnici. Può richiamare più tardi.",
        **{k: v for k, v in VOICE_CONFIG.items() if k in ['language', 'voice']}
    )
    response.hangup()
    
    return Response(str(response), mimetype="text/xml")


@app.route("/voice/fallback/", methods=['POST'])
def fallback_slash():
    return fallback()


# ============================================================================
# HEALTH CHECK & DEBUG
# ============================================================================

@app.route("/health", methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_calls": len(call_sessions),
        "orchestrator": "loaded",
        "config": {
            "llm_provider": config.LLM_PROVIDER,
            "rag_enabled": True
        }
    }, 200


@app.route("/debug/sessions", methods=['GET'])
def debug_sessions():
    """Debug endpoint to view active sessions (remove in production)"""
    return {
        "active_sessions": len(call_sessions),
        "sessions": {
            sid: {
                "turn_count": data["turn_count"],
                "start_time": data["start_time"].isoformat() if data["start_time"] else None,
                "intents": data["call_metadata"]["intents"]
            }
            for sid, data in call_sessions.items()
        }
    }, 200


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Configure logger
    logger.add(
        "logs/twilio_server_{time}.log",
        rotation="100 MB",
        retention="10 days",
        level="INFO"
    )
    
    logger.info("=" * 70)
    logger.info("🚀 Starting Twilio Voice Server")
    logger.info("=" * 70)
    logger.info(f"LLM Provider: {config.LLM_PROVIDER}")
    logger.info(f"Orchestrator: Loaded")
    logger.info(f"Voice: {VOICE_CONFIG['voice']} ({VOICE_CONFIG['language']})")
    logger.info("=" * 70)
    
    # Run Flask server
    port = int(os.getenv('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        use_reloader=False
    )
