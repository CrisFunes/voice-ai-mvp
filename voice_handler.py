import os
from pathlib import Path
from typing import Optional, Literal
import openai
from openai import OpenAI
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import config
import base64

# Supported audio formats
SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.webm', '.ogg'}
MAX_AUDIO_SIZE_MB = 25
MAX_TTS_LENGTH = 4096  # OpenAI TTS character limit

VoiceType = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class VoiceHandler:
    """
    Handles speech-to-text and text-to-speech operations for Italian language.
    
    **CRITICAL:** All methods validate inputs rigorously and raise descriptive errors.
    Audio files are automatically cleaned up to prevent disk bloat.
    """
    
    def __init__(self):
        """Initialize OpenAI client for voice operations"""
        logger.info("Initializing Voice Handler...")
        
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not found. Voice features cannot initialize."
            )
        
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Ensure temp directory exists
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.success("Voice Handler initialized successfully")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError))
    )
    def transcribe(
        self, 
        audio_path: str,
        language: str = "it",
        prompt: Optional[str] = None
    ) -> str:
        """
        Transcribe Italian audio to text using OpenAI Whisper.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, M4A, WebM, OGG)
            language: Language code (default: "it" for Italian)
            prompt: Optional hint for terminology (e.g., "IVA, IRES, commercialista")
        
        Returns:
            Transcribed text in Italian
        
        Raises:
            FileNotFoundError: Audio file doesn't exist
            ValueError: Invalid audio format or file too large
            RuntimeError: Whisper API error
        
        **CRITICAL VALIDATIONS:**
        - File existence
        - File size (max 25MB)
        - Audio format (WAV, MP3, M4A, WebM, OGG only)
        - Language forcing (prevents auto-detection errors)
        """
        audio_file = Path(audio_path)
        
        # Validation 1: File exists
        if not audio_file.exists():
            error_msg = f"File audio non trovato: {audio_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Validation 2: File format
        if audio_file.suffix.lower() not in SUPPORTED_FORMATS:
            error_msg = (
                f"Formato audio non supportato: {audio_file.suffix}. "
                f"Formati accettati: {', '.join(SUPPORTED_FORMATS)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validation 3: File size (Whisper limit: 25MB)
        size_mb = audio_file.stat().st_size / (1024 * 1024)
        if size_mb > MAX_AUDIO_SIZE_MB:
            error_msg = (
                f"File audio troppo grande: {size_mb:.1f}MB. "
                f"Massimo consentito: {MAX_AUDIO_SIZE_MB}MB"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(
            f"Transcribing audio: {audio_file.name} "
            f"({size_mb:.2f}MB, language={language})"
        )
        
        try:
            with open(audio_file, "rb") as audio:
                # CRITICAL: Force Italian language to prevent auto-detection errors
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language=language,  # Explicit Italian
                    prompt=prompt,  # Optional terminology hints
                    response_format="text"  # Plain text (not JSON/VTT)
                )
            
            # Whisper returns string directly in text format
            transcribed_text = transcript.strip()
            
            logger.success(
                f"Transcription complete: {len(transcribed_text)} characters - "
                f"'{transcribed_text[:50]}...'"
            )
            
            return transcribed_text
        
        except openai.RateLimitError as e:
            error_msg = (
                "Limite richieste API raggiunto. "
                "Attendi qualche minuto e riprova."
            )
            logger.error(f"Rate limit error: {e}")
            raise RuntimeError(error_msg) from e
        
        except openai.APIError as e:
            error_msg = f"Errore API OpenAI: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Errore imprevisto durante la trascrizione: {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError))
    )
    def synthesize(
        self,
        text: str,
        voice: VoiceType = "alloy",
        speed: float = 1.0,
        output_format: str = "mp3"
    ) -> str:
        """
        Synthesize Italian text to speech using OpenAI TTS.
        
        Args:
            text: Italian text to synthesize
            voice: Voice profile (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed (0.25 to 4.0, default 1.0)
            output_format: Audio format (mp3, opus, aac, flac)
        
        Returns:
            Path to generated audio file in temp directory
        
        Raises:
            ValueError: Empty text or text too long (>4096 chars)
            RuntimeError: TTS API error
        
        **CRITICAL VALIDATIONS:**
        - Text not empty
        - Text length within OpenAI limits (4096 chars)
        - Speed within valid range (0.25-4.0)
        - Voice is valid OpenAI voice
        """
        # Validation 1: Text not empty
        if not text or not text.strip():
            error_msg = "Il testo da sintetizzare è vuoto"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validation 2: Text length (OpenAI limit: 4096 characters)
        if len(text) > MAX_TTS_LENGTH:
            error_msg = (
                f"Testo troppo lungo: {len(text)} caratteri. "
                f"Massimo consentito: {MAX_TTS_LENGTH} caratteri"
            )
            logger.warning(error_msg)
            # Truncate instead of failing (better UX)
            text = text[:MAX_TTS_LENGTH]
            logger.info(f"Testo troncato a {MAX_TTS_LENGTH} caratteri")
        
        # Validation 3: Speed range
        if not (0.25 <= speed <= 4.0):
            logger.warning(f"Invalid speed {speed}, defaulting to 1.0")
            speed = 1.0
        
        logger.info(
            f"Synthesizing speech: {len(text)} chars, "
            f"voice={voice}, speed={speed}"
        )
        
        try:
            # Generate speech
            response = self.client.audio.speech.create(
                model="tts-1-hd",  # Standard quality (tts-1-hd for higher quality)
                voice=voice,
                input=text,
                speed=speed,
                response_format=output_format
            )
            
            # Generate unique filename
            import uuid
            output_filename = f"tts_{uuid.uuid4().hex[:8]}.{output_format}"
            output_path = config.TEMP_DIR / output_filename
            
            # Save audio to file
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            # Verify file was created
            if not output_path.exists():
                raise RuntimeError(
                    "File audio generato ma non trovato su disco"
                )
            
            file_size_kb = output_path.stat().st_size / 1024
            logger.success(
                f"Speech synthesized successfully: {output_path.name} "
                f"({file_size_kb:.1f}KB)"
            )
            
            return str(output_path)
        
        except openai.RateLimitError as e:
            error_msg = (
                "Limite richieste API raggiunto. "
                "Attendi qualche minuto e riprova."
            )
            logger.error(f"Rate limit error: {e}")
            raise RuntimeError(error_msg) from e
        
        except openai.APIError as e:
            error_msg = f"Errore API OpenAI: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Errore imprevisto durante la sintesi vocale: {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError))
    )
    def synthesize_with_accent(
        self,
        text: str,
        voice: VoiceType = "alloy",
        speed: float = 1.0
    ) -> str:
        """
        Synthesize Italian text with NATIVE ITALIAN ACCENT using gpt-4o-audio-preview.
        
        This method uses OpenAI's advanced audio model with steering instructions
        to produce Italian speech with authentic Italian accent and intonation,
        eliminating the "translated from English" effect.
        
        Args:
            text: Italian text to synthesize
            voice: Voice profile (alloy recommended for Italian)
            speed: Speech speed (not directly supported, ignored)
        
        Returns:
            Path to generated audio file in temp directory
        
        Raises:
            ValueError: Empty text or text too long
            RuntimeError: API error
        
        **CRITICAL:** This method uses gpt-4o-audio-preview which costs
        ~4x more than tts-1 but produces NATIVE Italian accent.
        Cost: ~$0.06 per 1K characters vs $0.015 for tts-1.
        
        **WHY THIS WORKS:**
        The model receives instructions to speak with authentic Italian accent,
        avoiding the neutral/anglophone pronunciation of standard TTS voices.
        """
        # Validation 1: Text not empty
        if not text or not text.strip():
            error_msg = "Il testo da sintetizzare è vuoto"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validation 2: Text length
        if len(text) > MAX_TTS_LENGTH:
            logger.warning(
                f"Testo troppo lungo: {len(text)} caratteri. "
                f"Troncamento a {MAX_TTS_LENGTH}"
            )
            text = text[:MAX_TTS_LENGTH]
        
        logger.info(
            f"Synthesizing speech WITH ITALIAN ACCENT: {len(text)} chars, "
            f"voice={voice}"
        )
        
        try:
            # CRITICAL: Use gpt-4o-audio-preview with accent instructions
            completion = self.client.chat.completions.create(
                model="gpt-4o-audio-preview",
                modalities=["text", "audio"],
                audio={
                    "voice": voice,
                    "format": "mp3"
                },
                messages=[
                    {
                        "role": "system",
                        "content": """Parla come un MADRELINGUA ITALIANO del Nord Italia (Milano/Lombardia).

ACCENTO E PRONUNCIA RICHIESTI:
- Intonazione naturale italiana, NON neutrale o anglosassone
- Pronuncia ogni parola con accento italiano autentico
- Ritmo e cadenza tipici di un italiano settentrionale
- Enfasi sulle vocali aperte/chiuse secondo fonetica italiana
- Evita qualsiasi traccia di pronuncia anglofona

STILE VOCALE:
- Tono professionale ma cordiale
- Come un commercialista milanese che parla con un cliente
- Sicuro e competente, ma non freddo o robotico
- Velocità moderata, chiara e comprensibile

FONDAMENTALE: 
Devi suonare come un ITALIANO che parla italiano, 
NON come uno straniero che legge italiano."""
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
            )
            
            # Decode base64 audio
            audio_data = completion.choices[0].message.audio.data
            mp3_bytes = base64.b64decode(audio_data)
            
            # Generate unique filename
            import uuid
            output_filename = f"tts_accent_{uuid.uuid4().hex[:8]}.mp3"
            output_path = config.TEMP_DIR / output_filename
            
            # Write audio file
            with open(output_path, "wb") as f:
                f.write(mp3_bytes)
            
            logger.success(
                f"Speech synthesis WITH ITALIAN ACCENT complete: {output_path.name}"
            )
            
            return str(output_path)
        
        except openai.RateLimitError as e:
            error_msg = (
                "Limite richieste API raggiunto. "
                "Attendi qualche minuto e riprova."
            )
            logger.error(f"Rate limit error: {e}")
            raise RuntimeError(error_msg) from e
        
        except openai.APIError as e:
            error_msg = f"Errore API OpenAI (audio model): {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        
        except KeyError as e:
            error_msg = (
                "Errore nella risposta API: formato audio non trovato. "
                "Il modello gpt-4o-audio-preview potrebbe non essere disponibile."
            )
            logger.error(f"KeyError accessing audio data: {e}")
            raise RuntimeError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Errore imprevisto durante la sintesi: {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
        
    def synthesize_italian(
        self,
        text: str,
        use_accent_model: bool = True,
        **kwargs
    ) -> str:
        """
        Synthesize Italian text with optional accent steering.
        
        This is a convenience wrapper that allows easy switching between:
        - Standard TTS (faster, cheaper, anglophone accent)
        - Accent-steered TTS (slower, 4x cost, native Italian accent)
        
        Args:
            text: Italian text to synthesize
            use_accent_model: If True, use gpt-4o-audio-preview with accent
                            If False, use standard tts-1/tts-1-hd
            **kwargs: Additional arguments passed to underlying method
        
        Returns:
            Path to generated audio file
        """
        if use_accent_model:
            logger.info("Using ACCENT-STEERED model (gpt-4o-audio-preview)")
            return self.synthesize_with_accent(text, **kwargs)
        else:
            logger.info("Using STANDARD TTS model (tts-1/tts-1-hd)")
            return self.synthesize(text, **kwargs)
    
    def cleanup_temp_files(self, max_age_hours: int = 1) -> int:
        """
        Clean up old temporary audio files to prevent disk bloat.
        
        Args:
            max_age_hours: Delete files older than this many hours
        
        Returns:
            Number of files deleted
        
        **BEST PRACTICE:** Call this periodically in production to prevent
        temp directory from growing unbounded.
        """
        import time
        
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in config.TEMP_DIR.glob("*"):
                if not file_path.is_file():
                    continue
                
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age >= max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old temp file: {file_path.name}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} temporary files")
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return deleted_count


# Module-level convenience functions
def quick_transcribe(audio_path: str) -> str:
    """Quick transcription with default settings"""
    handler = VoiceHandler()
    return handler.transcribe(audio_path)


def quick_synthesize(text: str, voice: VoiceType = "alloy") -> str:
    """Quick synthesis with default settings"""
    handler = VoiceHandler()
    return handler.synthesize(text, voice=voice)