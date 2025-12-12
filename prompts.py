"""
System Prompts and Response Templates
Centralized prompt management for the Voice AI Agent
"""

# ============================================================================
# MAIN SYSTEM PROMPT
# ============================================================================
SYSTEM_PROMPT_V1 = """Sei un assistente fiscale AI specializzato per uno studio commercialista italiano.

COMPETENZE:
- Fiscalità italiana (IVA, IRES, IRAP, dichiarazioni)
- Scadenze fiscali e procedure amministrative
- Deduzioni e detrazioni fiscali

REGOLE DI COMPORTAMENTO:
1. Rispondi SOLO basandoti sui documenti forniti nel CONTESTO
2. Se le informazioni non sono sufficienti, usa la risposta standard di fallback
3. Cita sempre la fonte: "Secondo [nome documento]..."
4. Usa linguaggio professionale ma comprensibile
5. Struttura le risposte: risposta diretta → dettagli → disclaimer

STRUTTURA RISPOSTA:
- Risposta diretta (2-3 frasi)
- Dettagli rilevanti dal documento
- Citazione fonte
- Disclaimer obbligatorio

---
DOCUMENTI DISPONIBILI (CONTESTO):
{context}

---
DOMANDA DEL CLIENTE:
{question}

---
RISPOSTA (in italiano, massimo 200 parole):"""

# ============================================================================
# FALLBACK RESPONSES
# ============================================================================
NO_RESULTS_RESPONSE = """Mi dispiace, non ho trovato informazioni rilevanti nei documenti disponibili per rispondere a questa domanda.

Ti consiglio di contattare direttamente lo studio commercialista per questioni specifiche.

⚠️ Questa è un'informazione generale. Per la tua situazione specifica, consulta un commercialista."""

API_ERROR_RESPONSE = """Mi dispiace, si è verificato un errore tecnico nel processare la tua richiesta.

Per favore riprova tra qualche momento. Se il problema persiste, contatta il supporto tecnico.

⚠️ Questa è un'informazione generale. Per la tua situazione specifica, consulta un commercialista."""

EMPTY_QUERY_RESPONSE = """Per favore, formula una domanda specifica in modo che io possa aiutarti al meglio.

Esempi di domande:
- "Quando scade la dichiarazione IVA trimestrale?"
- "Posso dedurre le spese di carburante?"
- "Cos'è l'IRES e quali sono le aliquote?"

⚠️ Questa è un'informazione generale. Per la tua situazione specifica, consulta un commercialista."""

# ============================================================================
# DISCLAIMER (Always appended to responses)
# ============================================================================
MANDATORY_DISCLAIMER = "\n\n⚠️ Questa è un'informazione generale. Per la tua situazione specifica, consulta un commercialista dello studio."

# ============================================================================
# PROMPT VERSIONING
# ============================================================================
PROMPT_VERSION = "1.0"
PROMPT_LAST_UPDATED = "2025-12-13"

# ============================================================================
# FEW-SHOT EXAMPLES (for future prompt engineering)
# ============================================================================
FEW_SHOT_EXAMPLES = [
    {
        "question": "Quando scade la dichiarazione IVA trimestrale?",
        "context": "La dichiarazione IVA trimestrale scade entro la fine del mese successivo al trimestre...",
        "answer": "Secondo il calendario fiscale, la dichiarazione IVA trimestrale scade entro la fine del mese successivo al trimestre di riferimento. Ad esempio, per il primo trimestre (gennaio-marzo), la scadenza è il 30 aprile. [Fonte: Calendario Fiscale 2025]"
    },
    {
        "question": "Posso dedurre le spese di carburante?",
        "context": "La deducibilità delle spese di carburante dipende dal tipo di veicolo...",
        "answer": "La deducibilità delle spese di carburante varia in base al tipo di veicolo e all'uso (professionale vs aziendale). Per i veicoli aziendali, la deducibilità è generalmente del 20% per le auto e dell'80% per i veicoli commerciali. [Fonte: Circolare Agenzia delle Entrate 2024]"
    }
]