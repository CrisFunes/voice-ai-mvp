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
    Entry node: Initialize conversation state.
    
    Responsibilities:
    - Set defaults
    - Log conversation start
    - Prepare for intent classification
    """
    logger.info("=== WELCOME NODE ===")
    
    # Initialize missing fields
    if "entities" not in state:
        state["entities"] = {}
    
    if "conversation_history" not in state:
        state["conversation_history"] = []
    
    if "confidence" not in state:
        state["confidence"] = 0.0
    
    if "requires_followup" not in state:
        state["requires_followup"] = False
    
    state["current_node"] = "welcome"
    
    # Log input
    input_text = state.get("transcript") or state.get("user_input", "")
    logger.info(f"User input: '{input_text[:100]}...'")
    
    # Add to history
    state["conversation_history"].append({
        "role": "user",
        "content": input_text,
        "timestamp": datetime.now().isoformat()
    })
    
    return state


def classify_intent_node(state: ConversationState) -> ConversationState:
    """
    Classify user intent using LLM.
    
    CRITICAL: This determines which service will handle the request.
    Accuracy here is essential for correct routing.
    """
    logger.info("=== CLASSIFY INTENT NODE ===")
    state["current_node"] = "classify_intent"
    
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
- lead: Nuovo potenziale cliente che chiede informazioni

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
        rag = RAGEngine()
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
    Execute action based on intent.
    
    Routes to appropriate service:
    - TAX_QUERY → RAG engine
    - BOOKING → Booking service (mock)
    - ROUTING → Routing service (mock)
    - OFFICE_INFO → Info service (mock)
    - LEAD → Lead service (mock)
    """
    logger.info("=== EXECUTE ACTION NODE ===")
    state["current_node"] = "execute_action"
    
    intent = state.get("intent", Intent.UNKNOWN)
    text = state.get("transcript") or state.get("user_input", "")
    
    logger.info(f"Executing action for intent: {intent.value}")
    
    try:
        if intent == Intent.TAX_QUERY:
            # Use RAG engine
            from rag_engine import RAGEngine
            
            rag = RAGEngine()
            result = rag.get_answer(text)
            
            state["response"] = result["answer"]
            state["action_taken"] = "tax_query_answered"
            
            # Store sources in entities for reference
            state["entities"]["sources"] = result.get("sources", [])
            
            logger.success("Tax query answered via RAG")
        
        elif intent == Intent.APPOINTMENT_BOOKING:
            # MOCK: Booking service
            # Version A: Replace with real BookingService
            
            entities = state.get("entities", {})
            date = entities.get("date", "non specificata")
            time = entities.get("time", "non specificata")
            
            if date == "non specificata" or time == "non specificata":
                state["response"] = (
                    "Per prenotare un appuntamento, ho bisogno di:\n"
                    "- Data preferita\n"
                    "- Orario preferito\n\n"
                    "Esempio: 'Vorrei un appuntamento domani alle 15:00'"
                )
                state["requires_followup"] = True
            else:
                # Mock: Simulate booking
                state["response"] = (
                    f"✅ Appuntamento prenotato!\n\n"
                    f"📅 Data: {date}\n"
                    f"🕐 Orario: {time}\n"
                    f"👤 Commercialista: Dott. Marco Rossi\n\n"
                    f"Riceverai una conferma via email."
                )
                state["action_taken"] = "appointment_created"
            
            logger.info(f"Booking request processed (mock)")
        
        elif intent == Intent.ACCOUNTANT_ROUTING:
            # MOCK: Routing service
            
            accountant_name = state["entities"].get("accountant_name", "")
            
            if not accountant_name:
                state["response"] = (
                    "Con quale commercialista vorresti parlare?\n\n"
                    "Alcuni dei nostri specialisti:\n"
                    "- Dott. Marco Rossi (Fiscalità)\n"
                    "- Dott.ssa Laura Bianchi (Paghe)\n"
                    "- Dott. Giuseppe Verdi (Societario)"
                )
                state["requires_followup"] = True
            else:
                # Mock: Simulate routing
                state["response"] = (
                    f"Il {accountant_name} è attualmente:\n"
                    f"🟢 Disponibile\n\n"
                    f"Posso:\n"
                    f"1. Prenotarti un appuntamento\n"
                    f"2. Inviargli un messaggio urgente\n\n"
                    f"Cosa preferisci?"
                )
                state["action_taken"] = "accountant_located"
            
            logger.info("Routing request processed (mock)")
        
        elif intent == Intent.OFFICE_INFO:
            # MOCK: Office info service
            
            # Detect what info they want
            text_lower = text.lower()
            
            if "orari" in text_lower or "aperto" in text_lower or "chiuso" in text_lower:
                state["response"] = (
                    "📅 Orari Studio:\n\n"
                    "Lunedì - Venerdì: 9:00 - 18:00\n"
                    "Sabato: 9:00 - 13:00\n"
                    "Domenica: Chiuso\n\n"
                    "⚠️ Durante agosto siamo chiusi dal 5 al 25."
                )
            elif "indirizzo" in text_lower or "dove" in text_lower:
                state["response"] = (
                    "📍 Sede:\n"
                    "Via Roma 123\n"
                    "20121 Milano (MI)\n\n"
                    "🚇 Metro: Duomo (M1/M3)\n"
                    "🚗 Parcheggio: Via Torino 45"
                )
            elif "contatto" in text_lower or "telefono" in text_lower or "email" in text_lower:
                state["response"] = (
                    "📞 Contatti:\n\n"
                    "Telefono: +39 02 1234567\n"
                    "Email: info@studiocommercialista.it\n"
                    "PEC: studio@pec.commercialista.it\n\n"
                    "Orario segreteria: 9:00 - 18:00"
                )
            else:
                # General info
                state["response"] = (
                    "ℹ️ Informazioni Studio:\n\n"
                    "📍 Via Roma 123, Milano\n"
                    "📞 +39 02 1234567\n"
                    "📧 info@studiocommercialista.it\n\n"
                    "Orari: Lun-Ven 9-18, Sab 9-13\n\n"
                    "Cosa vorresti sapere nello specifico?"
                )
            
            state["action_taken"] = "office_info_provided"
            logger.info("Office info provided (mock)")
        
        elif intent == Intent.LEAD_CAPTURE:
            # MOCK: Lead capture service
            
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
        
        logger.success("Orchestrator ready")
    
    def process(
        self, 
        user_input: str = None,
        audio_path: str = None,
        transcript: str = None
    ) -> ConversationState:
        """
        Process a user input through the conversation graph.
        
        Args:
            user_input: Text input (for text mode)
            audio_path: Path to audio file (for voice mode)
            transcript: Pre-transcribed text (if ASR done externally)
        
        Returns:
            Final conversation state with response
        """
        logger.info("="*70)
        logger.info("PROCESSING NEW CONVERSATION TURN")
        logger.info("="*70)
        
        # Build initial state
        initial_state: ConversationState = {}
        
        if transcript:
            initial_state["transcript"] = transcript
        elif audio_path:
            initial_state["audio_path"] = audio_path
        elif user_input:
            initial_state["user_input"] = user_input
        else:
            raise ValueError("Must provide user_input, audio_path, or transcript")
        
        # Run through graph
        try:
            final_state = self.app.invoke(initial_state)
            
            logger.info("="*70)
            logger.success("CONVERSATION TURN COMPLETED")
            logger.info(f"Intent: {final_state.get('intent', 'unknown')}")
            logger.info(f"Action: {final_state.get('action_taken', 'none')}")
            logger.info(f"Response length: {len(final_state.get('response', ''))} chars")
            logger.info("="*70)
            
            return final_state
        
        except Exception as e:
            logger.error(f"Orchestrator processing failed: {e}")
            
            # Return error state
            return {
                "user_input": user_input or "",
                "response": "Errore interno. Riprova o contatta lo studio.",
                "error": str(e),
                "intent": Intent.UNKNOWN,
                "current_node": "error"
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