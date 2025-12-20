"""
Performance and load testing
CRITICAL for production readiness
"""
import pytest
import time
from orchestrator import Orchestrator
from concurrent.futures import ThreadPoolExecutor, as_completed

class TestResponseTime:
    """Validate response times meet SLA"""
    
    def test_text_query_response_under_5_seconds(self):
        """Text queries should respond < 5s"""
        orchestrator = Orchestrator()
        
        start = time.time()
        result = orchestrator.process(user_input="Quando scade l'IVA?")
        duration = time.time() - start
        
        assert duration < 5.0, f"Response took {duration}s (target: <5s)"
    
    def test_booking_flow_response_under_8_seconds(self):
        """Booking (with DB write) should respond < 8s"""
        orchestrator = Orchestrator()
        
        start = time.time()
        result = orchestrator.process(
            user_input="Vorrei un appuntamento domani alle 15"
        )
        duration = time.time() - start
        
        assert duration < 8.0, f"Booking took {duration}s (target: <8s)"


class TestConcurrency:
    """Test system handles concurrent requests"""
    
    def test_10_concurrent_queries(self):
        """System should handle 10 simultaneous queries"""
        orchestrator = Orchestrator()
        
        def query():
            return orchestrator.process(user_input="Test query")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(query) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        # All should succeed
        assert len(results) == 10
        assert all(r.get("response") for r in results)
    
    def test_database_connection_pool(self):
        """Database should not exhaust connections"""
        orchestrator = Orchestrator()
        
        # 50 queries should not cause connection errors
        for i in range(50):
            result = orchestrator.process(
                user_input="A che ora chiudete?"
            )
            assert "error" not in result or result["error"] is None