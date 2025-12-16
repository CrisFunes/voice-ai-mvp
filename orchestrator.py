"""
LangGraph Orchestrator - Conversation State Machine
Manages multi-turn conversations with intent classification and routing
"""
from typing import TypedDict, Optional, List, Literal, Any
from enum import Enum
from datetime import datetime
from langgraph.graph import StateGraph, END
from loguru import logger
import json
from rag_engine import RAGEngine, get_rag_engine

# ============================================================================
# ENUMS & TYPES
# ============================================================================

class Intent(str, Enum):
    """User intent classification"""
    TAX_QUERY = "tax_query"              # Questions about tax law
    APPOINTMENT_BOOKING = "booking"       # Book/modify appointments
    ACCOUNTANT_ROUTING = "routing"        # Speak to specific accountant
    OFFICE_INFO = "office_info"           # Office hours, location, contact
    LEAD_CAPTURE = "lead"                 # New client inquiry
    UNKNOWN = "unknown"                   # Could not classify


class ConversationState(TypedDict, total=False):
    """
    Complete conversation state passed between nodes.
    
    CRITICAL: This is the SINGLE SOURCE OF TRUTH for conversation context.
    Every node reads from and writes to this state.
    """
    # Input
    user_input: str                       # Current user message (text)
    audio_path: Optional[str]             # Path to audio file (if voice mode)
    
    # Processing
    transcript: Optional[str]             # ASR output (if from audio)
    intent: Optional[Intent]              # Classified intent
    confidence: float                     # Intent confidence (0.0-1.0)
    
    # Entities extracted from input
    entities: dict                        # Extracted entities (dates, names, etc)
    
    # Context
    conversation_history: List[dict]      # Previous turns
    client_id: Optional[str]              # Identified client (if lookup succeeded)
    accountant_id: Optional[str]          # Target accountant (if routing)
    
    # Output
    response: str                         # Final response text
    response_audio_path: Optional[str]    # TTS output path
    action_taken: Optional[str]           # Action performed (e.g., "appointment_created")
    
    # Metadata
    current_node: str                     # Current processing node
    error: Optional[str]                  # Error message (if failed)
    requires_followup: bool               # True if needs more info


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def welcome_node(state: ConversationState) -> ConversationState:
    """
    Entry node: Initialize conversation state and generate greeting if needed.
    
    CRITICAL: This node now detects first-time calls and generates a proper greeting.
    """
    logger.info("=== WELCOME NODE ===")
    state["current_node"] = "welcome"
    
    user_input = state.get("user_input", state.get("transcript", ""))
    logger.info(f"User input: '{user_input[:50] if user_input else '(empty)'}...'")
    
    # Initialize conversation history
    if "conversation_history" not in state:
        state["conversation_history"] = []
    
    # Initialize entities
    if "entities" not in state:
        state["entities"] = {}
    
    # ✅ NEW: Detect first call (empty or very short input)
    if not user_input or len(user_input.strip()) < 3:
        logger.info("🎤 Detected first call - generating greeting")
        
        # Generate greeting
        greeting = (
            "Buongiorno! Benvenuto allo Studio Commercialista. "
            "Sono l'assistente virtuale e posso aiutarti con domande fiscali, "
            "prenotare appuntamenti o metterti in contatto con un commercialista. "
            "Come posso aiutarti oggi?"
        )
        
        # Set response directly (skip classification)
        state["response"] = greeting
        state["intent"] = Intent.UNKNOWN  # Mark as greeting, not a real query
        state["confidence"] = 1.0
        state["action_taken"] = "greeting_generated"
        
        # Add to conversation history
        state["conversation_history"].append({
            "role": "assistant",
            "content": greeting,
            "timestamp": datetime.now().isoformat(),
            "intent": "greeting",
            "action": "greeting_generated"
        })
        
        logger.success(f"✅ Greeting generated: {len(greeting)} chars")
    
    return state


def classify_intent_node(state: ConversationState) -> ConversationState:
    """
    Classify user intent using LLM.
    
    UPDATED: Skip classification if greeting already generated.
    """
    logger.info("=== CLASSIFY INTENT NODE ===")
    state["current_node"] = "classify_intent"
    
    # ✅ NEW: Skip if greeting already generated
    if state.get("action_taken") == "greeting_generated":
        logger.info("⏭️ Skipping classification - greeting already generated")
        return state
    
    # Get user input
    user_input = state.get("user_input", state.get("transcript", ""))
    
    # Validate input length
    if not user_input or len(user_input.strip()) < 3:
        logger.warning("Input too short for classification")
        state["intent"] = Intent.UNKNOWN
        state["confidence"] = 0.0
        state["entities"] = {}
        return state
    
    # Get input text (transcript if voice, else user_input)
    text = state.get("transcript") or state.get("user_input", "")
    
    if not text or len(text.strip()) < 3:
        logger.warning("Input too short for classification")
        state["intent"] = Intent.UNKNOWN
        state["confidence"] = 0.0
        state["error"] = "Input troppo breve"
        return state
    
    # Intent classification via LLM
    try:
        from rag_engine import RAGEngine
        import config
        
        # Build classification prompt
        prompt = f"""Analizza questa richiesta di un cliente di uno studio commercialista italiano e classifica l'intento.

INTENTI POSSIBILI:
- tax_query: Domande su fiscalità, tasse, IVA, IRES, scadenze fiscali
- booking: Prenotare, modificare, cancellare un appuntamento
- routing: Parlare con un commercialista specifico
- office_info: Orari ufficio, indirizzo, contatti
- lead: Nuovo potenziale cliente che chiede informazioni SPECIFICHE sui servizi
- unknown: Saluti generici, domande non correlate, messaggi poco chiari

IMPORTANTE: Se la richiesta è solo un saluto ("ciao", "come stai") o non ha intento chiaro, classifica come UNKNOWN.

RICHIESTA:
"{text}"

Rispondi SOLO con un JSON:
{{
  "intent": "tax_query|booking|routing|office_info|lead",
  "confidence": 0.0-1.0,
  "entities": {{
    "date": "YYYY-MM-DD se menzionata",
    "time": "HH:MM se menzionata",
    "accountant_name": "nome se menzionato",
    "tax_type": "IVA|IRES|IRAP se menzionato"
  }}
}}"""
        
        # Call LLM (reuse RAGEngine's LLM client)
        rag = get_rag_engine()
        response = rag._call_llm(prompt)
        
        # Parse JSON response
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
        
        result = json.loads(response)
        
        # Validate and set state
        intent_str = result.get("intent", "unknown")
        
        # Map to Intent enum
        intent_mapping = {
            "tax_query": Intent.TAX_QUERY,
            "booking": Intent.APPOINTMENT_BOOKING,
            "routing": Intent.ACCOUNTANT_ROUTING,
            "office_info": Intent.OFFICE_INFO,
            "lead": Intent.LEAD_CAPTURE
        }
        
        state["intent"] = intent_mapping.get(intent_str, Intent.UNKNOWN)
        state["confidence"] = float(result.get("confidence", 0.5))
        state["entities"] = result.get("entities", {})
        
        logger.success(
            f"Intent classified: {state['intent'].value} "
            f"(confidence: {state['confidence']:.2f})"
        )
        
        if state["entities"]:
            logger.info(f"Extracted entities: {state['entities']}")
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw response: {response}")
        state["intent"] = Intent.UNKNOWN
        state["confidence"] = 0.0
    
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        state["intent"] = Intent.UNKNOWN
        state["confidence"] = 0.0
        state["error"] = f"Errore classificazione: {str(e)}"
    
    return state


def execute_action_node(state: ConversationState) -> ConversationState:
    """
    Execute action based on intent using real service layer.
    
    Routes to appropriate service:
    - TAX_QUERY → RAG engine (real)
    - BOOKING → BookingService (real DB writes)
    - ROUTING → ClientService (real DB lookups)
    - OFFICE_INFO → OfficeInfoService (real DB queries)
    - LEAD → Lead capture (mock for now)
    """
    logger.info("=== EXECUTE ACTION NODE ===")
    state["current_node"] = "execute_action"
    
    intent = state.get("intent", Intent.UNKNOWN)
    text = state.get("transcript") or state.get("user_input", "")
    entities = state.get("entities", {})
    
    logger.info("=== EXECUTE ACTION NODE ===")
    state["current_node"] = "execute_action"
    
    # ✅ NEW: Skip if greeting already generated
    if state.get("action_taken") == "greeting_generated":
        logger.info("⏭️ Skipping action execution - greeting already generated")
        return state
    
    intent = state.get("intent", Intent.UNKNOWN)
    logger.info(f"Executing action for intent: {intent.value if intent else 'none'}")
    
    # Get database session
    from database import get_db_session
    
    try:
        if intent == Intent.TAX_QUERY:
            # ✅ Real RAG engine
            from rag_engine import RAGEngine
            
            rag = get_rag_engine()
            result = rag.get_answer(text)
            
            state["response"] = result["answer"]
            state["action_taken"] = "tax_query_answered"
            state["entities"]["sources"] = result.get("sources", [])
            
            logger.success("Tax query answered via RAG")
        
        elif intent == Intent.APPOINTMENT_BOOKING:
            # ✅ Real BookingService with DB writes
            from services import BookingService
            from datetime import datetime, timedelta
            import re
            
            # Extract entities - check both entities dict and raw text
            date_str = entities.get("date", "")
            time_str = entities.get("time", "")
            
            # If date not in entities, try to parse from original text
            text_lower = text.lower()
            
            # Detect relative days in text (check longer words first)
            if not date_str and "dopodomani" in text_lower:
                date_str = "dopodomani"
            # Detect "domani" (tomorrow) in text
            if not date_str and "domani" in text_lower:
                date_str = "domani"
            
            # Detect "oggi" (today)
            if not date_str and "oggi" in text_lower:
                date_str = "oggi"
            
            # Extract time from text if not in entities
            explicit_time = False
            if entities.get("time"):
                time_str = entities.get("time")
                explicit_time = True

            if not time_str:
                # Match patterns like "15:00", "alle 15", "15"
                time_match = re.search(r'(?:alle\s+)?(\d{1,2}):?(\d{2})?', text_lower)
                if time_match:
                    hour = time_match.group(1)
                    minute = time_match.group(2) or "00"
                    time_str = f"{hour}:{minute}"
                    explicit_time = True

            logger.info(f"Parsed booking request - date: {date_str}, time: {time_str}, explicit_time: {explicit_time}")
            # Parse date/time from entities
            if not date_str or not time_str:
                state["response"] = (
                    "Per prenotare un appuntamento, ho bisogno di:\n"
                    "- Data preferita\n"
                    "- Orario preferito\n\n"
                    "Esempio: 'Vorrei un appuntamento domani alle 15:00'"
                )
                state["requires_followup"] = True
                logger.warning("Missing date or time in booking request")
            else:
                try:
                    # Convert string to datetime
                    # Map relative date strings to actual dates
                    if "dopodomani" in date_str.lower():
                        appointment_date = datetime.now() + timedelta(days=2)
                        logger.info("Booking for day after tomorrow (dopodomani)")
                    elif "domani" in date_str.lower():
                        appointment_date = datetime.now() + timedelta(days=1)
                        logger.info("Booking for tomorrow (domani)")
                    elif "oggi" in date_str.lower():
                        appointment_date = datetime.now()
                        logger.info("Booking for today (oggi)")
                    else:
                        # Try to parse as date string
                        # For now, default to tomorrow
                        appointment_date = datetime.now() + timedelta(days=1)
                        logger.warning(f"Could not parse date '{date_str}', defaulting to tomorrow")
                    
                    # Parse time (e.g., "15:00" or "15")
                    if ":" in time_str:
                        hour = int(time_str.split(":")[0])
                        minute = int(time_str.split(":")[1])
                    else:
                        hour = int(time_str)
                        minute = 0
                    
                    # Validate business hours (9-18)
                    if hour < 9 or hour >= 18:
                        state["response"] = (
                            f"Mi dispiace, l'orario richiesto ({hour}:00) è fuori dall'orario d'ufficio.\n\n"
                            f"Orari disponibili: 9:00 - 18:00\n"
                            f"Scegli un altro orario."
                        )
                        state["requires_followup"] = True
                        logger.warning(f"Invalid hour: {hour}")
                    else:
                        appointment_datetime = appointment_date.replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                        
                        logger.info(f"Creating appointment for: {appointment_datetime}")
                        
                        # ✅ REAL DB WRITE
                        with get_db_session() as db:
                            booking_service = BookingService(db)
                            
                            # Get first client and accountant for demo
                            # Production: extract from conversation context
                            from models import Client, Accountant
                            client = db.query(Client).first()
                            accountant = db.query(Accountant).filter(
                                Accountant.status == "active"
                            ).first()
                            
                            if not client or not accountant:
                                raise ValueError("No clients or accountants in database")
                            
                            logger.info(f"Booking for client: {client.company_name}, accountant: {accountant.name}")

                            # Check requested slot availability and fallback to nearest if needed
                            available_slots = booking_service.check_availability(accountant.id, appointment_datetime, 60)
                            if appointment_datetime not in available_slots:
                                if explicit_time:
                                    # User explicitly requested this time; do not auto-reschedule
                                    raise ValueError(f"Slot {appointment_datetime} not available for accountant {accountant.id}")
                                else:
                                    # Choose nearest available slot (min abs diff)
                                    if available_slots:
                                        chosen = min(available_slots, key=lambda s: abs((s - appointment_datetime).total_seconds()))
                                        logger.warning(f"Requested slot {appointment_datetime} not available, choosing nearest {chosen}")
                                        appointment_datetime = chosen
                                    else:
                                        raise ValueError(f"Slot {appointment_datetime} not available for accountant {accountant.id}")

                            appointment = booking_service.create_appointment(
                                client_id=client.id,
                                accountant_id=accountant.id,
                                datetime=appointment_datetime,
                                duration=60,
                                notes=f"Booked via Voice AI: {text}"
                            )
                            
                            state["response"] = (
                                f"✅ Appuntamento confermato!\n\n"
                                f"📋 ID: {str(appointment.id)[:8]}...\n"
                                f"📅 Data: {appointment.datetime.strftime('%d/%m/%Y')}\n"
                                f"🕐 Orario: {appointment.datetime.strftime('%H:%M')}\n"
                                f"👤 Con: {accountant.name}\n"
                                f"🏢 Cliente: {client.company_name}\n\n"
                                f"Riceverai una conferma via email."
                            )
                            # If we adjusted the time, mention it
                            if appointment_datetime != appointment.datetime:
                                state["response"] += f"\n\nNota: l'orario richiesto non era disponibile. Ho prenotato il prossimo slot disponibile: {appointment.datetime.strftime('%H:%M')}"

                            state["action_taken"] = "appointment_created"
                            
                            logger.success(f"✅ REAL appointment created: ID={appointment.id}")
                
                except ValueError as ve:
                    logger.error(f"Validation error in booking: {ve}")
                    state["response"] = (
                        f"Mi dispiace, non posso creare l'appuntamento:\n{str(ve)}\n\n"
                        f"Per favore, riprova con data e ora valide."
                    )
                    state["error"] = str(ve)
                
                except Exception as e:
                    logger.error(f"Booking failed: {e}")
                    logger.exception("Full traceback:")
                    state["response"] = (
                        "Mi dispiace, non sono riuscito a creare l'appuntamento.\n"
                        "Per favore, contatta direttamente lo studio."
                    )
                    state["error"] = str(e)      

        elif intent == Intent.ACCOUNTANT_ROUTING:
            # ✅ Real ClientService for accountant lookup
            from services import ClientService
            from models import Accountant
            
            accountant_name = entities.get("accountant_name", "")
            
            if not accountant_name:
                # List available accountants from DB
                with get_db_session() as db:
                    accountants = db.query(Accountant).filter(
                        Accountant.status == "active"
                    ).limit(3).all()
                    
                    accountant_list = "\n".join([
                        f"- {acc.name} ({acc.specialization})"
                        for acc in accountants
                    ])
                    
                    state["response"] = (
                        f"Con quale commercialista vorresti parlare?\n\n"
                        f"Alcuni dei nostri specialisti:\n{accountant_list}"
                    )
                    state["requires_followup"] = True
            else:
                # Search for accountant in DB
                with get_db_session() as db:
                    accountant = db.query(Accountant).filter(
                        Accountant.name.ilike(f"%{accountant_name}%")
                    ).first()
                    
                    if accountant:
                        state["response"] = (
                            f"📞 {accountant.name}\n\n"
                            f"Specializzazione: {accountant.specialization}\n"
                            f"Email: {accountant.email}\n"
                            f"Telefono: {accountant.phone}\n\n"
                            f"Vuoi prenotare un appuntamento?"
                        )
                        state["action_taken"] = "accountant_located"
                    else:
                        state["response"] = (
                            f"Non ho trovato '{accountant_name}' nel nostro database.\n"
                            f"Vuoi che ti mostri l'elenco completo dei commercialisti?"
                        )
                        state["requires_followup"] = True
            
            logger.info("Routing request processed with real DB lookup")
        
        elif intent == Intent.OFFICE_INFO:
            # ✅ Real OfficeInfoService
            from services import OfficeInfoService
            
            text_lower = text.lower()
            
            with get_db_session() as db:
                info_service = OfficeInfoService(db)
                
                # More robust matching for office hours (handle 'chiudete', 'chiude', 'aperto')
                if "orari" in text_lower or "apert" in text_lower or "chiud" in text_lower:
                    # Get office hours from DB
                    hours = info_service.get_office_hours()
                    state["response"] = f"📅 Orari Studio:\n\n{hours}"
                
                elif "indirizzo" in text_lower or "dove" in text_lower:
                    # Get address from DB
                    address = info_service.get_address()
                    if address:
                        state["response"] = f"📍 Sede:\n{address}"
                    else:
                        state["response"] = "Indirizzo non disponibile al momento."
                
                elif "contatto" in text_lower or "telefono" in text_lower or "email" in text_lower:
                    # Get contact info from DB
                    contacts = info_service.get_contact_info()
                    contact_str = "\n".join([f"{k}: {v}" for k, v in contacts.items()])
                    state["response"] = f"📞 Contatti:\n\n{contact_str}"
                
                else:
                    # General info
                    address = info_service.get_address()
                    contacts = info_service.get_contact_info()
                    phone = contacts.get("office_phone", "N/A")
                    email = contacts.get("office_email", "N/A")
                    
                    state["response"] = (
                        f"ℹ️ Informazioni Studio:\n\n"
                        f"📍 {address}\n"
                        f"📞 {phone}\n"
                        f"📧 {email}\n\n"
                        f"Cosa vorresti sapere nello specifico?"
                    )
            
            state["action_taken"] = "office_info_provided"
            logger.info("Office info provided from DB")
        
        elif intent == Intent.LEAD_CAPTURE:
            # Mock for now (Version A will have real CRM integration)
            state["response"] = (
                "Benvenuto! Siamo lieti di conoscerti.\n\n"
                "Per offrirti la migliore consulenza, ho bisogno di qualche informazione:\n\n"
                "1. Sei un privato o hai un'azienda?\n"
                "2. Di cosa hai bisogno? (es: aprire partita IVA, consulenza fiscale, ecc.)\n\n"
                "Oppure preferisci fissare un appuntamento conoscitivo gratuito?"
            )
            state["action_taken"] = "lead_captured"
            state["requires_followup"] = True
            
            logger.info("Lead captured (mock)")
        
        else:
            # UNKNOWN intent
            state["response"] = (
                "Mi dispiace, non ho capito bene la tua richiesta.\n\n"
                "Posso aiutarti con:\n"
                "📊 Domande fiscali (IVA, IRES, scadenze)\n"
                "📅 Prenotare appuntamenti\n"
                "👤 Parlare con un commercialista\n"
                "ℹ️ Informazioni sullo studio\n\n"
                "Cosa ti serve?"
            )
            state["action_taken"] = "clarification_requested"
            state["requires_followup"] = True
            
            logger.warning("Unknown intent, requesting clarification")
    
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        logger.exception("Full traceback:")
        state["response"] = (
            "Mi dispiace, si è verificato un errore.\n"
            "Riprova o chiama direttamente lo studio al +39 02 1234567."
        )
        state["error"] = str(e)
    
    return state


def generate_response_node(state: ConversationState) -> ConversationState:
    """
    Finalize response: format, add disclaimers, prepare for TTS.
    
    CRITICAL: This is the last step before returning to user.
    Ensure response is professional, complete, and correct.
    """
    logger.info("=== GENERATE RESPONSE NODE ===")
    state["current_node"] = "generate_response"
    
    response = state.get("response", "")
    intent = state.get("intent", Intent.UNKNOWN)
    
    if "action_taken" not in state:
        state["action_taken"] = None

    # Add disclaimer for tax queries
    if intent == Intent.TAX_QUERY and response:
        if "⚠️" not in response:  # Don't duplicate
            response += (
                "\n\n⚠️ Questa è un'informazione generale. "
                "Per la tua situazione specifica, consulta un commercialista."
            )
    
    # Add to conversation history
    state["conversation_history"].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now().isoformat(),
        "intent": intent.value if intent else "unknown",
        "action": state.get("action_taken", "none")
    })
    
    state["response"] = response
    
    logger.success(f"Response finalized ({len(response)} chars)")
    
    return state


def should_end(state: ConversationState) -> Literal["end"]:
    """
    Conditional edge: Determine if conversation should end.
    
    For now, always end (single-turn).
    In V.A with multi-turn, check requires_followup.
    """
    # Version B: Always end (single-turn conversations)
    # Version A: Check requires_followup, continue if True
    
    if state.get("requires_followup", False):
        logger.info("Followup required, but V.B is single-turn. Ending anyway.")
    
    return "end"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_conversation_graph() -> StateGraph:
    """
    Build the LangGraph state machine.
    
    Flow:
    welcome → classify_intent → execute_action → generate_response → end
    """
    logger.info("Building conversation graph...")
    
    # Create graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("welcome", welcome_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # Define edges
    workflow.set_entry_point("welcome")
    workflow.add_edge("welcome", "classify_intent")
    workflow.add_edge("classify_intent", "execute_action")
    workflow.add_edge("execute_action", "generate_response")
    
    # Conditional edge: end or continue
    workflow.add_conditional_edges(
        "generate_response",
        should_end,
        {"end": END}
    )
    
    logger.success("Conversation graph built successfully")
    
    return workflow


# ============================================================================
# ORCHESTRATOR CLASS
# ============================================================================

class Orchestrator:
    """
    Main orchestrator: Manages conversation flow via LangGraph.
    
    Usage:
        orchestrator = Orchestrator()
        result = orchestrator.process("Quando scade l'IVA?")
        print(result["response"])
    """
    
    def __init__(self):
        """Initialize orchestrator with compiled graph"""
        logger.info("Initializing Orchestrator...")
        
        workflow = create_conversation_graph()
        self.app = workflow.compile()
        
        # Pre-warm RAG Engine (load once at startup)
        logger.info("Pre-warming RAG Engine...")
        self.rag = get_rag_engine()  # ✅ Carga anticipada
        logger.success("RAG Engine pre-warmed and ready")
        
        logger.success("Orchestrator ready")
    
    def process(
        self, 
        user_input: str = None,
        audio_path: str = None,
        transcript: str = None,
        context: dict = None
    ) -> ConversationState:
        """
        Process a user input through the conversation graph.
        
        Args:
            user_input: Text input (for text mode)
            audio_path: Path to audio file (for voice mode)
            transcript: Pre-transcribed text (if ASR done externally)
            context: Previous conversation context (for multi-turn)
        
        Returns:
            Final conversation state with response AND context for next turn
        """
        logger.info("="*70)
        logger.info("PROCESSING NEW CONVERSATION TURN")
        logger.info("="*70)
        
        # Build initial state (preserve context if provided)
        initial_state: ConversationState = context.copy() if context else {}
        
        if transcript:
            initial_state["transcript"] = transcript
        elif audio_path:
            initial_state["audio_path"] = audio_path
        elif user_input:
            initial_state["user_input"] = user_input
        else:
            raise ValueError("Must provide user_input, audio_path, or transcript")
        
        # Initialize context fields if not present
        if "conversation_history" not in initial_state:
            initial_state["conversation_history"] = []
        if "entities" not in initial_state:
            initial_state["entities"] = {}
        
        # Run through graph
        try:
            final_state = self.app.invoke(initial_state)
            
            logger.info("="*70)
            logger.success("CONVERSATION TURN COMPLETED")
            logger.info(f"Intent: {final_state.get('intent', 'unknown')}")
            logger.info(f"Action: {final_state.get('action_taken', 'none')}")
            logger.info(f"Response length: {len(final_state.get('response', ''))} chars")
            logger.info("="*70)
            
            # ✅ ADD CONTEXT TO RESULT FOR MULTI-TURN CONVERSATIONS
            # Preserve state for next turn
            final_state["context"] = {
                "conversation_history": final_state.get("conversation_history", []),
                "entities": final_state.get("entities", {}),
                "client_id": final_state.get("client_id"),
                "accountant_id": final_state.get("accountant_id"),
                "intent": final_state.get("intent"),
                "confidence": final_state.get("confidence", 0.0)
            }
            
            return final_state
        
        except Exception as e:
            logger.error(f"Orchestrator processing failed: {e}")
            
            # Return error state WITH CONTEXT
            return {
                "user_input": user_input or "",
                "response": "Errore interno. Riprova o contatta lo studio.",
                "error": str(e),
                "intent": Intent.UNKNOWN,
                "current_node": "error",
                "context": {}  # ✅ Empty context on error
            }

# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ORCHESTRATOR.PY - LangGraph State Machine Test")
    print("="*70)
    
    # Initialize
    orchestrator = Orchestrator()
    
    # Test scenarios
    test_cases = [
        ("Quando scade la dichiarazione IVA?", Intent.TAX_QUERY),
        ("Vorrei prenotare un appuntamento", Intent.APPOINTMENT_BOOKING),
        ("Posso parlare con il Dott. Rossi?", Intent.ACCOUNTANT_ROUTING),
        ("A che ora chiudete?", Intent.OFFICE_INFO),
        ("Sono un nuovo cliente", Intent.LEAD_CAPTURE),
    ]
    
    print("\nRunning test scenarios...\n")
    
    for i, (query, expected_intent) in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {query}")
        print(f"Expected intent: {expected_intent.value}")
        print('='*70)
        
        result = orchestrator.process(user_input=query)
        
        actual_intent = result.get("intent", Intent.UNKNOWN)
        response = result.get("response", "")
        
        # Check result
        if actual_intent == expected_intent:
            print(f"✅ Intent matched: {actual_intent.value}")
        else:
            print(f"⚠️  Intent mismatch: got {actual_intent.value}, expected {expected_intent.value}")
        
        print(f"\n📝 Response ({len(response)} chars):")
        print(response[:200] + "..." if len(response) > 200 else response)
        
        if result.get("action_taken"):
            print(f"\n🎯 Action: {result['action_taken']}")
    
    print("\n" + "="*70)
    print("✅ ORCHESTRATOR TEST COMPLETE")
    print("="*70)