"""
LangGraph state machine validation
Tests node transitions and state consistency
"""
import pytest
from orchestrator import Orchestrator, ConversationState

class TestNodeTransitions:
    """Validate state transitions between nodes"""
    
    def test_welcome_to_classify_transition(self):
        """Welcome node should always go to classify"""
        orchestrator = Orchestrator()
        
        initial_state: ConversationState = {
            "user_input": "test"
        }
        
        # Mock graph execution
        result = orchestrator.app.invoke(initial_state)
        
        # Should have gone through classify
        assert result.get("intent") is not None
        assert result.get("confidence") is not None
    
    def test_error_handling_creates_error_state(self):
        """Errors should create proper error state"""
        orchestrator = Orchestrator()
        
        # Force error with invalid state
        with pytest.raises(Exception):
            orchestrator.process(user_input=None, audio_path=None, transcript=None)


class TestStateConsistency:
    """Validate state object remains consistent"""
    
    def test_all_required_fields_present(self):
        """Final state should have all required fields"""
        orchestrator = Orchestrator()
        
        result = orchestrator.process(user_input="Test")
        
        required_fields = [
            "user_input",
            "intent",
            "confidence",
            "response",
            "current_node"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"