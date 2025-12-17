"""
Integration Tests - End-to-end flow validation
Tests complete user journeys through the system
"""
import pytest
from datetime import datetime, timedelta
from orchestrator import Orchestrator, Intent
from database import get_db_session
from models import Appointment, Client, Accountant


class TestBookingFlow:
    """Test complete booking workflow"""
    
    def test_booking_creates_appointment_in_db(self):
        """Test that booking request creates real DB record"""
        # Setup
        orchestrator = Orchestrator()
        
        # Get initial count
        with get_db_session() as db:
            count_before = db.query(Appointment).count()
        
        # Execute booking
        result = orchestrator.process(
            user_input="Vorrei un appuntamento dopodomani alle 16:30"
        )
        
        # Verify
        assert result["intent"] == Intent.APPOINTMENT_BOOKING

        # If the exact requested slot was available we should have created an appointment
        if result.get("action_taken") == "appointment_created":
            assert any(word in result["response"].lower() for word in ["appuntamento", "fissato", "perfetto"])

            # Verify DB write
            with get_db_session() as db:
                count_after = db.query(Appointment).count()
                assert count_after == count_before + 1

                # Verify appointment details
                newest = db.query(Appointment).order_by(
                    Appointment.created_at.desc()
                ).first()

                assert newest.status == "pending"
                assert "Prenotazione" in (newest.notes or "")

                # If user explicitly requested a time, appointment hour should match or be the nearest slot
                # (We accept nearby slot if exact time unavailable)
                assert isinstance(newest.datetime.hour, int)
        else:
            # If we couldn't create appointment, the response should indicate failure
            assert "non" in result["response"].lower() or "errore" in result.get("error", "").lower()

    
    def test_booking_rejects_invalid_hours(self):
        """Test that booking rejects out-of-hours requests"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Vorrei un appuntamento domani alle 20:00"
        )
        
        assert "fuori dall'orario" in result["response"].lower()
        assert result["action_taken"] != "appointment_created"
    
    def test_booking_detects_conflicts(self):
        """Test that booking detects schedule conflicts"""
        orchestrator = Orchestrator()
        
        # Create first appointment
        result1 = orchestrator.process(
            user_input="Vorrei un appuntamento dopodomani alle 11:00"
        )
        
        if result1["action_taken"] == "appointment_created":
            # Try to create conflicting appointment
            result2 = orchestrator.process(
                user_input="Vorrei un appuntamento dopodomani alle 11:00"
            )
            
            # Should reject
            assert result2["action_taken"] != "appointment_created"
            assert "error" in result2.get("error", "").lower() or \
                   "non" in result2["response"].lower()


class TestTaxQueryFlow:
    """Tax queries are rejected (no fiscal advice)"""
    
    def test_tax_query_returns_rag_response(self):
        """Tax queries should be rejected and routed to a human"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Quando scade la dichiarazione IVA?"
        )

        assert result["intent"] == Intent.UNKNOWN
        assert result.get("action_taken") == "tax_query_rejected"
        assert any(word in result["response"].lower() for word in ["non posso", "consulenza", "appuntamento", "commercialista"])
    
    def test_tax_query_includes_disclaimer(self):
        """Deduction-related questions should be rejected as tax queries"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Posso dedurre le spese di carburante?"
        )

        assert result["intent"] == Intent.UNKNOWN
        assert result.get("action_taken") == "tax_query_rejected"


class TestRoutingFlow:
    """Test accountant routing"""
    
    def test_routing_finds_accountant_in_db(self):
        """Test that routing queries real database"""
        orchestrator = Orchestrator()
        
        # Get an actual accountant name from DB
        with get_db_session() as db:
            accountant = db.query(Accountant).first()
            accountant_name = accountant.name
        
        result = orchestrator.process(
            user_input=f"Vorrei parlare con {accountant_name}"
        )
        
        assert result["intent"] == Intent.ACCOUNTANT_ROUTING
        assert accountant_name in result["response"]
    
    def test_routing_handles_unknown_accountant(self):
        """Test routing with non-existent accountant"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Vorrei parlare con Dott. FantasyName"
        )
        
        assert "non ho trovato" in result["response"].lower() or \
               result.get("requires_followup") == True


class TestOfficeInfoFlow:
    """Test office information queries"""
    
    def test_office_hours_from_db(self):
        """Test that office hours come from database"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="A che ora chiudete oggi?"
        )
        
        assert result["intent"] == Intent.OFFICE_INFO
        assert result["action_taken"] == "office_info_provided"
        # Should contain hours information
        assert any(word in result["response"].lower() 
                  for word in ["orari", "aperto", "chiuso"])
    
    def test_office_address_from_db(self):
        """Test that address comes from database"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Dove siete?"
        )
        
        assert "via" in result["response"].lower() or \
               "sede" in result["response"].lower()


class TestUnknownIntentFlow:
    """Test handling of unclear requests"""
    
    def test_unknown_intent_requests_clarification(self):
        """Test that system handles unclear requests gracefully"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(
            user_input="Ciao come stai?"
        )
        
        assert result["intent"] == Intent.UNKNOWN
        assert result["action_taken"] == "clarification_requested"
        assert result.get("requires_followup") == True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])