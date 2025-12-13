# test_voice_handler.py
"""
Unit tests for voice_handler.py
Run with: pytest test_voice_handler.py -v
"""

import pytest
from pathlib import Path
from voice_handler import VoiceHandler
import config

# Create test fixtures
@pytest.fixture
def voice_handler():
    """Create VoiceHandler instance"""
    return VoiceHandler()

@pytest.fixture
def sample_text():
    """Sample Italian text for TTS testing"""
    return "Buongiorno, sono un assistente fiscale AI per lo studio commercialista."


class TestVoiceHandlerInitialization:
    """Test voice handler initialization"""
    
    def test_initialization_success(self, voice_handler):
        """Voice handler should initialize successfully"""
        assert voice_handler.client is not None
    
    def test_temp_directory_created(self):
        """Temp directory should be created on init"""
        handler = VoiceHandler()
        assert config.TEMP_DIR.exists()


class TestTranscriptionValidation:
    """Test input validation for transcription"""
    
    def test_transcribe_nonexistent_file(self, voice_handler):
        """Should raise FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError):
            voice_handler.transcribe("nonexistent_file.wav")
    
    def test_transcribe_invalid_format(self, voice_handler, tmp_path):
        """Should raise ValueError for unsupported format"""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("dummy")
        
        with pytest.raises(ValueError, match="Formato audio non supportato"):
            voice_handler.transcribe(str(invalid_file))
    
    def test_transcribe_file_too_large(self, voice_handler, tmp_path):
        """Should raise ValueError for files >25MB"""
        # Create a 26MB dummy file
        large_file = tmp_path / "large.wav"
        large_file.write_bytes(b"0" * (26 * 1024 * 1024))
        
        with pytest.raises(ValueError, match="troppo grande"):
            voice_handler.transcribe(str(large_file))


class TestSynthesisValidation:
    """Test input validation for synthesis"""
    
    def test_synthesize_empty_text(self, voice_handler):
        """Should raise ValueError for empty text"""
        with pytest.raises(ValueError, match="vuoto"):
            voice_handler.synthesize("")
    
    def test_synthesize_text_too_long(self, voice_handler):
        """Should truncate text >4096 chars instead of failing"""
        long_text = "a" * 5000
        result_path = voice_handler.synthesize(long_text)
        
        # Should succeed (truncate, not fail)
        assert Path(result_path).exists()
        
        # Cleanup
        Path(result_path).unlink()
    
    def test_synthesize_invalid_speed(self, voice_handler, sample_text):
        """Should default to 1.0 for invalid speed"""
        # Should not raise, should default
        result_path = voice_handler.synthesize(sample_text, speed=10.0)
        assert Path(result_path).exists()
        Path(result_path).unlink()


class TestSynthesisSuccess:
    """Test successful TTS synthesis"""
    
    def test_synthesize_creates_file(self, voice_handler, sample_text):
        """Should create MP3 file"""
        result_path = voice_handler.synthesize(sample_text)
        
        assert Path(result_path).exists()
        assert Path(result_path).suffix == ".mp3"
        assert Path(result_path).stat().st_size > 0
        
        # Cleanup
        Path(result_path).unlink()
    
    def test_synthesize_different_voices(self, voice_handler, sample_text):
        """Should work with different voice profiles"""
        voices = ["alloy", "echo", "nova"]
        
        for voice in voices:
            result_path = voice_handler.synthesize(sample_text, voice=voice)
            assert Path(result_path).exists()
            Path(result_path).unlink()


class TestTempFileCleanup:
    """Test temporary file cleanup"""
    
    def test_cleanup_old_files(self, voice_handler, sample_text):
        """Should delete files older than max_age"""
        # Create a temp file
        audio_path = voice_handler.synthesize(sample_text)
        assert Path(audio_path).exists()
        
        # Cleanup files older than 0 hours (all files)
        deleted = voice_handler.cleanup_temp_files(max_age_hours=0)
        
        # File should be deleted
        assert deleted >= 1
        assert not Path(audio_path).exists()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])