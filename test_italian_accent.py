# test_italian_accent.py
"""Quick test for Italian accent TTS"""

from voice_handler import VoiceHandler
from pathlib import Path

def test_italian_accent():
    """Test the new accent-steered TTS"""
    
    handler = VoiceHandler()
    
    # Test text with difficult Italian words
    test_texts = [
        "Buongiorno, sono il suo commercialista di fiducia a Milano.",
        "La dichiarazione IVA trimestrale scade il giorno quindici del mese successivo.",
        "Per l'IRES, l'aliquota ordinaria è attualmente del ventiquattro per cento.",
    ]
    
    print("\n=== Testing STANDARD TTS (anglophone accent) ===")
    for i, text in enumerate(test_texts):
        print(f"\nTest {i+1}: {text[:50]}...")
        path = handler.synthesize_italian(text, use_accent_model=False)
        print(f"✓ Generated: {path}")
        assert Path(path).exists()
    
    print("\n=== Testing ACCENT-STEERED TTS (Italian native) ===")
    for i, text in enumerate(test_texts):
        print(f"\nTest {i+1}: {text[:50]}...")
        path = handler.synthesize_italian(text, use_accent_model=True)
        print(f"✓ Generated: {path}")
        assert Path(path).exists()
    
    print("\n✅ All tests passed! Compare the audio files manually.")
    print("   Listen to both versions and verify the accent difference.")

if __name__ == "__main__":
    test_italian_accent()