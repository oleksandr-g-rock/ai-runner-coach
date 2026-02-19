"""
Unit tests for the transcription service.
"""
import os
import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
from transcription_service import TranscriptionService, create_transcription_service


class TestTranscriptionService(unittest.TestCase):
    """Test cases for TranscriptionService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_api_key = "test_api_key_12345"
        self.test_audio_path = "/tmp/test_audio.ogg"
        self.test_transcription_text = "Привіт, це тестове повідомлення"
    
    @patch.dict(os.environ, {"GROQ_WHISPER_API_KEY": "test_env_key"})
    def test_init_with_env_variable(self):
        """Test initialization with environment variable."""
        service = TranscriptionService()
        self.assertEqual(service.api_key, "test_env_key")
    
    def test_init_with_api_key_parameter(self):
        """Test initialization with API key parameter."""
        service = TranscriptionService(api_key=self.test_api_key)
        self.assertEqual(service.api_key, self.test_api_key)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with self.assertRaises(ValueError) as context:
            TranscriptionService()
        self.assertIn("GROQ_WHISPER_API_KEY", str(context.exception))
    
    @patch('transcription_service.Groq')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    def test_transcribe_audio_success(self, mock_file, mock_groq_class):
        """Test successful audio transcription."""
        # Setup mock
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        mock_transcription = MagicMock()
        mock_transcription.text = self.test_transcription_text
        mock_client.audio.transcriptions.create.return_value = mock_transcription
        
        # Create service and transcribe
        service = TranscriptionService(api_key=self.test_api_key)
        result = service.transcribe_audio(self.test_audio_path)
        
        # Assertions
        self.assertEqual(result, self.test_transcription_text)
        mock_file.assert_called_once_with(self.test_audio_path, "rb")
        mock_client.audio.transcriptions.create.assert_called_once()
        
        # Check that the correct parameters were passed
        call_args = mock_client.audio.transcriptions.create.call_args
        self.assertEqual(call_args.kwargs['model'], 'whisper-large-v3')
        self.assertEqual(call_args.kwargs['temperature'], 0)
        self.assertEqual(call_args.kwargs['response_format'], 'verbose_json')
    
    @patch('transcription_service.Groq')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    def test_transcribe_audio_with_language(self, mock_file, mock_groq_class):
        """Test audio transcription with specific language."""
        # Setup mock
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        mock_transcription = MagicMock()
        mock_transcription.text = self.test_transcription_text
        mock_client.audio.transcriptions.create.return_value = mock_transcription
        
        # Create service and transcribe with language
        service = TranscriptionService(api_key=self.test_api_key)
        result = service.transcribe_audio(self.test_audio_path, language="uk")
        
        # Assertions
        self.assertEqual(result, self.test_transcription_text)
        
        # Check that language was passed
        call_args = mock_client.audio.transcriptions.create.call_args
        self.assertEqual(call_args.kwargs['language'], 'uk')
    
    @patch('transcription_service.Groq')
    def test_transcribe_audio_file_not_found(self, mock_groq_class):
        """Test transcription with non-existent file."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        
        service = TranscriptionService(api_key=self.test_api_key)
        
        with self.assertRaises(FileNotFoundError):
            service.transcribe_audio("/non/existent/file.ogg")
    
    @patch('transcription_service.Groq')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    def test_transcribe_audio_api_error(self, mock_file, mock_groq_class):
        """Test transcription when API raises an error."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        service = TranscriptionService(api_key=self.test_api_key)
        
        with self.assertRaises(Exception) as context:
            service.transcribe_audio(self.test_audio_path)
        
        self.assertIn("API Error", str(context.exception))
    
    @patch.dict(os.environ, {"GROQ_WHISPER_API_KEY": "factory_test_key"})
    def test_create_transcription_service_factory(self):
        """Test factory function creates service correctly."""
        service = create_transcription_service()
        self.assertIsInstance(service, TranscriptionService)
        self.assertEqual(service.api_key, "factory_test_key")


if __name__ == '__main__':
    unittest.main()
