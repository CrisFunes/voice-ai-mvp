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
    "hints": "IVA, IRES, appuntamento, commercialista, scadenza, dichiarazione"
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
    
    # ✅ CORRECTO: Solo enviamos saludo, NO llamamos orchestrator
    response = VoiceResponse()
    
    # Saluto iniziale (breve, naturale, senza riferimenti a "AI")
    response.say(
        "Buongiorno, Studio Commercialista. Come posso aiutarLa?",
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
        # ✅ ESTO MEJORA LA CALIDAD
        hints="IVA, IRES, appuntamento, commercialista",
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
    transcript = request.values.get('SpeechResult', '').strip()
    confidence = request.values.get('Confidence', '0.0')
    
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
    
    # Handle empty input
    if not transcript or len(transcript) < 3:
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
        
        # Orchestrator maintains conversation history internally
        result = orchestrator.process(user_input=transcript)
        
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
