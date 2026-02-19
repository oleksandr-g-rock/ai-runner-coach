"""
Integration tests for voice message handling in the Telegram bot.
"""
import os
import sys
import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from telegram import Update, Message, Chat, Voice, User
from telegram.ext import ContextTypes


# Set up environment variables before importing main
test_env = {
    "TELEGRAM_TOKEN": "test_token",
    "OPENROUTER_API_KEY": "test_openrouter_key",
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "GROQ_WHISPER_API_KEY": "test_groq_key",
    "STRAVA_CLIENT_ID": "test_strava_id",
    "STRAVA_CLIENT_SECRET": "test_strava_secret",
    "BASE_URL": "http://test.local"
}


class TestVoiceMessageHandling(unittest.TestCase):
    """Integration tests for voice message handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chat_id = "12345"
        self.test_voice_file_id = "test_voice_file_123"
        self.test_transcription = "Привіт, як справи?"
        
    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_voice_authorized_user(self, mock_db_conn, mock_groq):
        """Test voice message handling for authorized user."""
        # Import main module with mocked dependencies
        import main
        
        # Setup database mock
        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": True}
        
        # Setup transcription service mock
        mock_transcription_service = Mock()
        mock_transcription_service.transcribe_audio.return_value = self.test_transcription
        
        # Patch main module
        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'transcription_service', mock_transcription_service), \
             patch.object(main, 'run_agent_cycle', return_value="Bot response"):
            
            # Create mock update and context
            update = self._create_mock_update()
            context = self._create_mock_context()
            
            # Mock file download
            mock_file = AsyncMock()
            mock_file.download_to_drive = AsyncMock()
            context.bot.get_file.return_value = mock_file
            
            # Run the async handler
            asyncio.run(main.handle_voice(update, context))
            
            # Verify profile was checked
            mock_db.get_profile.assert_called_once_with(self.chat_id)
            
            # Verify file was downloaded
            context.bot.get_file.assert_called_once_with(self.test_voice_file_id)
            
            # Verify transcription was called
            self.assertTrue(mock_transcription_service.transcribe_audio.called)
            
            # Verify response was sent
            self.assertTrue(update.message.reply_text.called)
    
    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_voice_unauthorized_user(self, mock_db_conn, mock_groq):
        """Test voice message handling for unauthorized user."""
        import main
        
        # Setup database mock
        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": False}
        
        with patch.object(main, 'db', mock_db):
            # Create mock update and context
            update = self._create_mock_update()
            context = self._create_mock_context()
            
            # Run the async handler
            asyncio.run(main.handle_voice(update, context))
            
            # Verify access was denied
            mock_db.get_profile.assert_called_once_with(self.chat_id)
            
            # Verify error message was sent
            update.message.reply_text.assert_called()
            call_args = update.message.reply_text.call_args
            self.assertIn("password", call_args[0][0].lower())
    
    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_voice_no_transcription_service(self, mock_db_conn, mock_groq):
        """Test voice message handling when transcription service is not available."""
        import main
        
        # Setup database mock
        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": True}
        
        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'transcription_service', None):
            
            # Create mock update and context
            update = self._create_mock_update()
            context = self._create_mock_context()
            
            # Run the async handler
            asyncio.run(main.handle_voice(update, context))
            
            # Verify error message was sent
            update.message.reply_text.assert_called()
            call_args = update.message.reply_text.call_args
            self.assertIn("not configured", call_args[0][0].lower())
    
    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_voice_transcription_error(self, mock_db_conn, mock_groq):
        """Test voice message handling when transcription fails."""
        import main
        
        # Setup database mock
        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": True}
        
        # Setup transcription service to raise error
        mock_transcription_service = Mock()
        mock_transcription_service.transcribe_audio.side_effect = Exception("Transcription failed")
        
        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'transcription_service', mock_transcription_service):
            
            # Create mock update and context
            update = self._create_mock_update()
            context = self._create_mock_context()
            
            # Mock file download
            mock_file = AsyncMock()
            mock_file.download_to_drive = AsyncMock()
            context.bot.get_file.return_value = mock_file
            
            # Run the async handler
            asyncio.run(main.handle_voice(update, context))
            
            # Verify error was handled gracefully
            self.assertTrue(update.message.reply_text.called)
    
    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_voice_no_message(self, mock_db_conn, mock_groq):
        """Test voice message handler with no message in update."""
        import main
        
        mock_db = Mock()
        
        with patch.object(main, 'db', mock_db):
            # Create update without message
            update = Mock(spec=Update)
            update.message = None
            context = self._create_mock_context()
            
            # Run the async handler
            asyncio.run(main.handle_voice(update, context))
            
            # Verify database was not accessed
            mock_db.get_profile.assert_not_called()
    
    def _create_mock_update(self):
        """Helper to create a mock Update object."""
        update = Mock(spec=Update)
        message = AsyncMock(spec=Message)
        chat = Mock(spec=Chat)
        voice = Mock(spec=Voice)
        user = Mock(spec=User)
        
        # Set up relationships
        message.chat = chat
        message.voice = voice
        message.from_user = user
        
        # Set attributes
        chat.id = int(self.chat_id)
        message.chat_id = int(self.chat_id)
        voice.file_id = self.test_voice_file_id
        
        # Mock async methods
        message.reply_text = AsyncMock()
        message.chat.send_action = AsyncMock()
        
        update.message = message
        
        return update
    
    def _create_mock_context(self):
        """Helper to create a mock ContextTypes.DEFAULT_TYPE object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        bot = AsyncMock()
        bot.get_file = AsyncMock()
        context.bot = bot
        return context


if __name__ == '__main__':
    unittest.main()

