# ANÁLISIS DE CAPACIDADES Y PLAN DE REFACTORING
**Fecha:** 16 de Diciembre 2025
**Objetivo:** Adaptar el agente a los requisitos explícitos del cliente

---

## 🎯 SITUACIÓN ACTUAL

### Sistema Actual (a limpiar/refactorizar)
El proyecto actual tiene:
- **RAG Engine** con documentos fiscales (730, IVA, IRES, deduciones)
- **1708 chunks** de documentos fiscales procesados
- Sistema de conversación con **intent classification** hardcodeado
- Servicios implementados: `BookingService`, `ClientService`, `OfficeInfoService`
- Orquestador basado en LangGraph con flujos hardcodeados

### ⚠️ PROBLEMA CRÍTICO
El cliente **NO QUIERE** que el agente responda preguntas fiscales:
> "The agent must not respond to tax issues or replace the accountant. They must only perform call centre duties."

**ACCIÓN REQUERIDA:** Eliminar/desactivar completamente el RAG de documentos fiscales.

---

## 📋 REQUISITOS DEL CLIENTE

### 4 CAPACIDADES PRINCIPALES (DEMO)

#### 1. GESTIONE APPUNTAMENTI (Agenda Management)
**Descripción:** Gestión completa de agenda - crear, modificar, cancelar citas

**Ejemplos de conversación:**
- "Pronto, vorrei prendere appuntamento con il Dottor Rossi per la settimana prossima."
- "Senti, domani alle 15:00 non riesco proprio a venire, possiamo fare giovedì?"
- "Il Dottore è in studio oggi pomeriggio? Vorrei passare un attimo."
- "Devo portarvi le fatture del trimestre, quando trovo qualcuno in segreteria?"
- "Mi conferma l'orario dell'appuntamento di domani? Non mi ricordo se era alle 10 o alle 11."
- "Vorrei parlare con chi si occupa delle paghe, devo fissare un incontro."

**Componentes necesarios:**
- ✅ `BookingService` (ya existe)
- ✅ `Appointment` model (ya existe)
- ✅ `Accountant` model (ya existe)
- ✅ `Client` model (ya existe)
- 🔧 Validación de disponibilidad en tiempo real
- 🔧 Manejo de conflictos de horario
- 🔧 Confirmación y recordatorios

**Flujo de conversación:**
```
USUARIO: "Vorrei prendere appuntamento con il Dottor Rossi"
  ↓
[Intent: APPOINTMENT_BOOKING]
  ↓
[Extract entities: accountant_name="Rossi", timeframe="la settimana prossima"]
  ↓
[BookingService.check_availability(accountant_id, next_week)]
  ↓
AGENTE: "Certo! Il Dottor Rossi ha disponibilità martedì 19 alle 10:00, 
         mercoledì 20 alle 14:30, o giovedì 21 alle 11:00. Quale preferisce?"
  ↓
USUARIO: "Giovedì alle 11 va bene"
  ↓
[BookingService.create_appointment(client, accountant, datetime, duration)]
  ↓
AGENTE: "Perfetto! Ho prenotato l'appuntamento per giovedì 21 dicembre 
         alle 11:00 con il Dottor Rossi. Riceverà una conferma via email."
```

---

#### 2. SMISTAMENTO E CONTATTO (Call Routing)
**Descripción:** Dirigir llamadas al profesional correcto o tomar mensaje

**Ejemplos de conversación:**
- "Buongiorno, cercavo la Dott.ssa Bianchi per una questione sulle assunzioni."
- "C'è Luca? Devo chiedergli una cosa veloce sulla fatturazione elettronica."
- "Vorrei parlare con la segretaria che segue la mia contabilità."
- "È urgente, mi faccia richiamare dal Dottore appena si libera."
- "Chi si occupa delle pratiche SCIA? Vorrei parlarci."
- "Sono Mario Rossi, il Dottore mi aveva detto di richiamarlo oggi."

**Componentes necesarios:**
- ✅ `Accountant` model con especialización (ya existe)
- ✅ `Client` model con accountant_id asignado (ya existe)
- 🆕 `CallLog` model (nuevo - para registrar intentos de contacto)
- 🆕 Routing logic basado en especialización
- 🆕 Sistema de mensajería/callback
- 🔧 Identificación de cliente por nombre/teléfono

**Flujo de conversación:**
```
USUARIO: "Buongiorno, cercavo la Dott.ssa Bianchi"
  ↓
[Intent: ACCOUNTANT_ROUTING]
  ↓
[Extract: accountant_name="Bianchi"]
  ↓
[ClientService.find_accountant(name="Bianchi")]
  ↓
[Accountant.status == ACTIVE? Disponible?]
  ↓
CASO A - DISPONIBLE:
  AGENTE: "Un momento, la trasferisco subito alla Dott.ssa Bianchi."
  [Transfer call - simulado en demo]

CASO B - OCUPADO:
  AGENTE: "La Dott.ssa Bianchi è al momento impegnata. 
           Vuole che le faccia richiamare o preferisce lasciare un messaggio?"
  ↓
  USUARIO: "Sì, mi faccia richiamare"
  ↓
  [CallLog.create(client_id, accountant_id, reason, callback_requested=True)]
  ↓
  AGENTE: "Perfetto, la Dott.ssa Bianchi la richiamerà appena possibile. 
           Può confermarmi il suo numero di telefono?"
```

---

#### 3. AMMINISTRAZIONE DELLO STUDIO (Office Info)
**Descripción:** Información general del estudio - horarios, ubicación, procedimientos

**Ejemplos de conversación:**
- "A che ora chiudete stasera?"
- "Siete aperti venerdì pomeriggio o fate ponte?"
- "Avete cambiato indirizzo o siete sempre in Via Roma?"

**Componentes necesarios:**
- ✅ `OfficeInfoService` (ya existe)
- 🔧 Información estructurada en config o DB:
  - Horarios de apertura/cierre
  - Dirección y contacto
  - Días festivos/cierres
  - Documentos requeridos para diferentes trámites

**Flujo de conversación:**
```
USUARIO: "A che ora chiudete stasera?"
  ↓
[Intent: OFFICE_INFO]
  ↓
[Extract: query_type="hours", timeframe="today evening"]
  ↓
[OfficeInfoService.get_hours(day="today")]
  ↓
AGENTE: "Oggi chiudiamo alle 18:00. Se ha bisogno di venire dopo l'orario, 
         può prendere appuntamento chiamando domani mattina."
```

**Información a mantener (sin RAG):**
```python
OFFICE_INFO = {
    "hours": {
        "monday-friday": "9:00-13:00, 14:30-18:00",
        "saturday": "9:00-12:00",
        "sunday": "Closed"
    },
    "address": "Via Roma 123, 20121 Milano",
    "phone": "+39 02 1234567",
    "email": "info@studiocommercialista.it",
    "holidays": ["2025-12-25", "2025-12-26", "2026-01-01"]
}
```

---

#### 4. NUOVI CLIENTI (Lead Generation & Capture)
**Descripción:** Capturar información de potenciales clientes nuevos

**Ejemplos de conversación:**
- "Buongiorno, vorrei aprire una Partita IVA, quanto costa una consulenza?"
- "Seguite anche il regime forfettario?"
- "Sarei interessato a cambiare commercialista, posso fissare un colloquio conoscitivo?"
- "Vi occupate anche di associazioni no-profit?"

**Componentes necesarios:**
- ✅ `Lead` model (ya existe en models.py)
- 🔧 Lead qualification questions
- 🔧 Captura de datos estructurados
- 🔧 Categorización automática

**Flujo de conversación:**
```
USUARIO: "Buongiorno, vorrei aprire una Partita IVA"
  ↓
[Intent: LEAD_CAPTURE]
  ↓
[Lead category: NEW_BUSINESS]
  ↓
AGENTE: "Certamente! La prima consulenza è gratuita. 
         Per preparare l'incontro, può dirmi il tipo di attività che vorrebbe aprire?"
  ↓
USUARIO: "Consulenza informatica freelance"
  ↓
AGENTE: "Perfetto. Qual è il suo nome?"
  ↓
USUARIO: "Marco Verdi"
  ↓
AGENTE: "Grazie Marco. Può darmi un numero di telefono e email per contattarla?"
  ↓
[Lead.create(name, phone, email, category, notes)]
  ↓
AGENTE: "Ottimo! Ho registrato la sua richiesta. 
         Un nostro consulente la contatterà entro 24 ore per fissare 
         un colloquio conoscitivo. Ha altre domande?"
```

---

## 🔧 COMPONENTES DEL SISTEMA ACTUAL

### Base de Datos (models.py)
```
✅ Accountant     - Comercialistas del estudio
✅ Client         - Clientes existentes
✅ Appointment    - Citas programadas
✅ Lead           - Potenciales clientes
🆕 CallLog        - Registro de llamadas (NUEVO)
🆕 OfficeConfig   - Configuración del estudio (NUEVO)
```

### Servicios (services/)
```
✅ BookingService      - Gestión de citas
✅ ClientService       - Búsqueda de clientes
✅ OfficeInfoService   - Información del estudio
🆕 RoutingService      - Lógica de ruteo (NUEVO)
🆕 LeadService         - Captura de leads (NUEVO)
```

### Orquestador (orchestrator.py)
```
⚠️ REFACTORIZAR - Actualmente tiene:
- Welcome node
- Intent classification (5 intents, incluyendo TAX_QUERY a eliminar)
- Routing nodes hardcodeados
- RAG integration (a eliminar)

🎯 NUEVO DISEÑO:
- Intent classification simplificado (4 intents principales)
- Conversation flow más flexible
- Sin RAG de documentos
- Multi-turn conversation tracking
```

### RAG Engine (rag_engine.py)
```
❌ DESACTIVAR - El cliente NO quiere respuestas fiscales
Opciones:
A) Eliminar completamente
B) Comentar/desactivar
C) Mantener código pero sin uso

✅ RECOMENDACIÓN: Opción C - Mantener código comentado 
   por si el cliente cambia de opinión en el futuro
```

---

## 📊 MATRIZ DE CAPACIDADES

| Capacidad | Intent | Service(s) | DB Tables | Estado |
|-----------|--------|-----------|-----------|--------|
| **Crear cita** | APPOINTMENT_BOOKING | BookingService | Appointment, Accountant, Client | ✅ Funcional |
| **Modificar cita** | APPOINTMENT_BOOKING | BookingService | Appointment | 🔧 Mejorar |
| **Cancelar cita** | APPOINTMENT_BOOKING | BookingService | Appointment | 🔧 Mejorar |
| **Confirmar cita** | APPOINTMENT_BOOKING | BookingService | Appointment | 🆕 Nuevo |
| **Ruteo de llamadas** | ACCOUNTANT_ROUTING | RoutingService, ClientService | Accountant, Client, CallLog | 🔧 Mejorar |
| **Mensaje callback** | ACCOUNTANT_ROUTING | RoutingService | CallLog | 🆕 Nuevo |
| **Horarios oficina** | OFFICE_INFO | OfficeInfoService | OfficeConfig | ✅ Funcional |
| **Dirección** | OFFICE_INFO | OfficeInfoService | OfficeConfig | ✅ Funcional |
| **Documentos requeridos** | OFFICE_INFO | OfficeInfoService | OfficeConfig | 🆕 Nuevo |
| **Captura lead** | LEAD_CAPTURE | LeadService | Lead | 🔧 Mejorar |
| **Calificación lead** | LEAD_CAPTURE | LeadService | Lead | 🆕 Nuevo |
| **Seguimiento lead** | LEAD_CAPTURE | LeadService | Lead | 🆕 Nuevo |

---

## 🚀 PLAN DE REFACTORING

### FASE 1: LIMPIEZA (2-3 horas)
**Objetivo:** Eliminar elementos fiscales y simplificar

1. **Desactivar RAG de documentos fiscales**
   - [ ] Comentar código en `rag_engine.py`
   - [ ] Remover llamadas a RAG en `orchestrator.py`
   - [ ] Eliminar intent `TAX_QUERY`
   - [ ] Limpiar prompts fiscales en `prompts.py`

2. **Limpiar base de datos ChromaDB**
   - [ ] Respaldar `chroma_db/` actual
   - [ ] Limpiar colección o crear nueva vacía
   - [ ] Documentar cambio

3. **Simplificar intents**
   ```python
   # ANTES (5 intents)
   TAX_QUERY, APPOINTMENT_BOOKING, ACCOUNTANT_ROUTING, OFFICE_INFO, LEAD_CAPTURE
   
   # DESPUÉS (4 intents)
   APPOINTMENT_BOOKING, ACCOUNTANT_ROUTING, OFFICE_INFO, LEAD_CAPTURE
   ```

### FASE 2: NUEVOS COMPONENTES (3-4 horas)

1. **Agregar CallLog model**
   ```python
   class CallLog(Base):
       __tablename__ = "call_logs"
       id = Column(String(36), primary_key=True)
       client_id = Column(String(36), ForeignKey("clients.id"))
       accountant_id = Column(String(36), ForeignKey("accountants.id"))
       datetime = Column(DateTime, nullable=False)
       reason = Column(Text)
       callback_requested = Column(Boolean, default=False)
       status = Column(String(20))  # pending/completed/cancelled
   ```

2. **Agregar OfficeConfig model**
   ```python
   class OfficeConfig(Base):
       __tablename__ = "office_config"
       key = Column(String(50), primary_key=True)
       value = Column(Text, nullable=False)
       description = Column(Text)
   ```

3. **Crear RoutingService**
   - Lógica de búsqueda de accountant por nombre
   - Check disponibilidad
   - Crear CallLog si no disponible

4. **Mejorar LeadService**
   - Lead qualification flow
   - Structured data capture
   - Auto-categorization

### FASE 3: REFACTORIZAR ORQUESTADOR (4-5 horas)

1. **Rediseñar flujo de conversación**
   - Multi-turn support mejorado
   - Context tracking más robusto
   - Entity extraction refinado

2. **Implementar sub-flows específicos**
   - `appointment_booking_flow()` - Gestión completa de citas
   - `routing_flow()` - Ruteo y callbacks
   - `office_info_flow()` - Info general
   - `lead_capture_flow()` - Captura estructurada

3. **Mejorar manejo de estado**
   ```python
   ConversationState:
       - current_flow: str  # active sub-flow
       - flow_step: int     # step within flow
       - collected_data: dict  # accumulated entities
       - needs_confirmation: bool
   ```

### FASE 4: NUEVOS TESTS (3-4 horas)

**Test scenarios basados en requisitos del cliente:**

1. **test_appointment_scenarios.py**
   ```python
   - test_book_appointment_simple()
   - test_book_appointment_with_conflicts()
   - test_modify_appointment()
   - test_cancel_appointment()
   - test_confirm_appointment_time()
   ```

2. **test_routing_scenarios.py**
   ```python
   - test_route_to_available_accountant()
   - test_route_busy_accountant_callback()
   - test_route_by_specialization()
   - test_identify_existing_client()
   ```

3. **test_office_info_scenarios.py**
   ```python
   - test_get_office_hours()
   - test_get_address()
   - test_check_holiday_closure()
   ```

4. **test_lead_capture_scenarios.py**
   ```python
   - test_capture_new_business_lead()
   - test_capture_freelance_lead()
   - test_qualify_lead_with_questions()
   ```

### FASE 5: CONFIGURACIÓN Y DATOS (2 horas)

1. **Seed data actualizado**
   - Accountants realistas (nombres italianos)
   - Clients de ejemplo
   - Office config básica
   - Horarios y holidays

2. **Prompts en italiano**
   - Greeting natural
   - Error messages
   - Confirmation messages
   - Fallback responses

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Sprint 1: Limpieza (Día 1)
- [ ] Backup del proyecto actual
- [ ] Desactivar RAG engine
- [ ] Limpiar ChromaDB
- [ ] Eliminar TAX_QUERY intent
- [ ] Actualizar prompts
- [ ] Commit: "refactor: disable tax Q&A, focus on call center"

### Sprint 2: Nuevos Models (Día 1-2)
- [ ] Crear CallLog model
- [ ] Crear OfficeConfig model
- [ ] Migración de DB
- [ ] Seed data actualizado
- [ ] Commit: "feat: add CallLog and OfficeConfig models"

### Sprint 3: Nuevos Services (Día 2)
- [ ] Implementar RoutingService
- [ ] Mejorar LeadService
- [ ] Actualizar OfficeInfoService
- [ ] Unit tests para services
- [ ] Commit: "feat: implement routing and lead services"

### Sprint 4: Refactor Orchestrator (Día 2-3)
- [ ] Rediseñar conversation flows
- [ ] Implementar sub-flows
- [ ] Mejorar state management
- [ ] Integration tests
- [ ] Commit: "refactor: redesign conversation orchestrator"

### Sprint 5: Tests E2E (Día 3)
- [ ] Test scenarios de appointments
- [ ] Test scenarios de routing
- [ ] Test scenarios de office info
- [ ] Test scenarios de lead capture
- [ ] Commit: "test: add comprehensive E2E scenarios"

### Sprint 6: Demo Prep (Día 3)
- [ ] Script de demo
- [ ] Audio samples de prueba
- [ ] Documentation
- [ ] Video walkthrough
- [ ] Commit: "docs: add demo script and examples"

---

## 🎯 CRITERIOS DE ÉXITO

### Funcionales
- ✅ Agente puede gestionar citas (crear, modificar, cancelar)
- ✅ Agente puede rutear llamadas correctamente
- ✅ Agente proporciona info de oficina
- ✅ Agente captura leads estructuradamente
- ✅ NO responde preguntas fiscales (redirige a accountant)

### Técnicos
- ✅ Tests E2E pasan (>90%)
- ✅ DB persistente funciona
- ✅ Multi-turn conversations funcionan
- ✅ Voice pipeline completo (ASR → Process → TTS)
- ✅ Código limpio y documentado

### Demo
- ✅ 4 escenarios principales funcionan en vivo
- ✅ Respuestas naturales en italiano
- ✅ Tiempos de respuesta < 3 segundos
- ✅ Manejo de errores elegante

---

## 📞 PRÓXIMOS PASOS

1. **Revisar este documento con el cliente** - Confirmar que el plan está alineado
2. **Priorizar capacidades** - ¿Todas son igual de importantes para la demo?
3. **Definir seed data** - ¿Qué accountants, clientes y horarios usar?
4. **Comenzar Sprint 1** - Limpieza y preparación

**¿Procedo con la implementación?**
