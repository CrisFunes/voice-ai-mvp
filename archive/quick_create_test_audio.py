# quick_create_test_audio.py
from voice_handler import VoiceHandler

voice = VoiceHandler()

test_queries = {
    "test_iva": "Quando scade la dichiarazione IVA trimestrale?",
    "test_deduzioni": "Posso dedurre le spese di carburante?",
    "test_ires": "Cos'è l'IRES e quali sono le aliquote?"
}

# Create test_data directory
from pathlib import Path
Path("test_data").mkdir(exist_ok=True)

for filename, text in test_queries.items():
    # Synthesize
    audio_path = voice.synthesize(text, voice="nova")
    
    # Move to test_data
    new_path = f"test_data/{filename}.mp3"
    Path(audio_path).rename(new_path)
    print(f"✓ Created: {new_path}")