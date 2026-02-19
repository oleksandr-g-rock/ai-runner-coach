"""
Transcription service using Groq's Whisper API.
Handles voice message transcription from audio files to text.
"""
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files using Groq's Whisper API."""
    
    def __init__(self, api_key=None):
        """
        Initialize the transcription service.
        
        Args:
            api_key: Groq API key. If None, reads from GROQ_WHISPER_API_KEY env variable.
        """
        self.api_key = api_key or os.environ.get("GROQ_WHISPER_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_WHISPER_API_KEY environment variable is not set")
        self.client = Groq(api_key=self.api_key)
    
    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe an audio file to text.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            language: Optional language code (e.g., 'uk' for Ukrainian, 'en' for English).
                     If None, the model will auto-detect the language.
        
        Returns:
            str: Transcribed text
            
        Raises:
            Exception: If transcription fails
        """
        try:
            with open(audio_file_path, "rb") as file:
                # Read the file content
                file_content = file.read()
                filename = os.path.basename(audio_file_path)
                
                # Prepare transcription parameters
                transcription_params = {
                    "file": (filename, file_content),
                    "model": "whisper-large-v3",
                    "temperature": 0,
                    "response_format": "verbose_json",
                }
                
                # Add language parameter if specified
                if language:
                    transcription_params["language"] = language
                
                # Create transcription
                transcription = self.client.audio.transcriptions.create(**transcription_params)
                
                logger.info(f"Successfully transcribed audio file: {audio_file_path}")
                return transcription.text
                
        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_file_path}")
            raise
        except Exception as e:
            logger.error(f"Transcription error for {audio_file_path}: {e}")
            raise


def create_transcription_service():
    """Factory function to create a transcription service instance."""
    return TranscriptionService()
