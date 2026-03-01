"""
Tests for bot features: temporal context, memory management, profile display,
and agent cycle behavior.
"""
import os
import sys
import unittest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
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


class TestTemporalContext(unittest.TestCase):
    """Tests for date/time awareness in the agent cycle."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_system_prompt_includes_current_datetime(self, mock_db_conn, mock_groq):
        """Verify that run_agent_cycle includes current date/time in the system prompt."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Test response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            main.run_agent_cycle("12345", "Hello")

            # Check that the system message includes CURRENT DATE/TIME
            call_args = mock_llm.chat.completions.create.call_args
            messages = call_args[1]['messages'] if 'messages' in call_args[1] else call_args[0][0]
            system_msg = messages[0]['content']
            self.assertIn("CURRENT DATE/TIME:", system_msg)

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_system_prompt_datetime_format(self, mock_db_conn, mock_groq):
        """Verify that the datetime in system prompt follows expected format."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            main.run_agent_cycle("12345", "What day is it?")

            call_args = mock_llm.chat.completions.create.call_args
            messages = call_args[1]['messages'] if 'messages' in call_args[1] else call_args[0][0]
            system_msg = messages[0]['content']
            # Should contain UTC formatted datetime
            self.assertIn("UTC", system_msg)
            # Should have year in the datetime
            current_year = str(datetime.now(timezone.utc).year)
            self.assertIn(current_year, system_msg)


class TestHistoryTimestamps(unittest.TestCase):
    """Tests for timestamp handling in conversation history."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_history_entries_include_timestamps(self, mock_db_conn, mock_groq):
        """Verify that new history entries include timestamps."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Bot response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            main.run_agent_cycle("12345", "Hello bot")

            # Check that update_history was called with timestamped entries
            mock_db.update_history.assert_called_once()
            saved_history = mock_db.update_history.call_args[0][1]

            # Should have 2 entries (user + assistant)
            self.assertEqual(len(saved_history), 2)

            # Both entries should have timestamps
            for entry in saved_history:
                self.assertIn("timestamp", entry)
                self.assertIn("UTC", entry["timestamp"])

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_old_history_without_timestamps_handled(self, mock_db_conn, mock_groq):
        """Verify that old history entries without timestamps are handled gracefully."""
        import main

        # Simulate old history entries without timestamps
        old_history = [
            {"role": "user", "content": "Old message"},
            {"role": "assistant", "content": "Old response"}
        ]

        mock_db = Mock()
        mock_db.get_history.return_value = old_history
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "New response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            # Should not raise any exceptions
            result = main.run_agent_cycle("12345", "New message")
            self.assertEqual(result, "New response")

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_history_with_timestamps_prepended_to_content(self, mock_db_conn, mock_groq):
        """Verify that timestamps from history are prepended to message content for LLM."""
        import main

        history_with_ts = [
            {"role": "user", "content": "Hello", "timestamp": "2026-02-20 10:00 UTC"},
            {"role": "assistant", "content": "Hi there", "timestamp": "2026-02-20 10:00 UTC"}
        ]

        mock_db = Mock()
        mock_db.get_history.return_value = history_with_ts
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            main.run_agent_cycle("12345", "Test")

            call_args = mock_llm.chat.completions.create.call_args
            messages = call_args[1]['messages'] if 'messages' in call_args[1] else call_args[0][0]

            # History messages should have timestamps prepended
            # messages[0] is system, messages[1] & [2] are history, messages[3] is new user msg
            history_user_msg = messages[1]['content']
            self.assertIn("[2026-02-20 10:00 UTC]", history_user_msg)
            self.assertIn("Hello", history_user_msg)


class TestMemoryManagement(unittest.TestCase):
    """Tests for memory/profile saving behavior."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_system_prompt_restricts_memory_to_sport_facts(self, mock_db_conn, mock_groq):
        """Verify system prompt instructs to save only sport-related facts."""
        import main

        # Check the SYSTEM_PROMPT text
        self.assertIn("ONLY save facts directly related to sport, fitness, and health", main.SYSTEM_PROMPT)
        self.assertIn("DO NOT save", main.SYSTEM_PROMPT)
        self.assertIn("casual conversations", main.SYSTEM_PROMPT)

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_save_profile_info_tool_description_specific(self, mock_db_conn, mock_groq):
        """Verify save_profile_info tool description mentions sport-specific saving."""
        import main

        save_tool = None
        for tool in main.TOOLS_SCHEMA:
            if tool['function']['name'] == 'save_profile_info':
                save_tool = tool
                break

        self.assertIsNotNone(save_tool)
        desc = save_tool['function']['description']
        self.assertIn("sport", desc.lower())
        self.assertIn("Do NOT save casual", desc)

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_save_profile_info_function(self, mock_db_conn, mock_groq):
        """Test the save_profile_info function saves data correctly."""
        import main

        mock_db = Mock()
        mock_db.save_profile_data.return_value = True

        with patch.object(main, 'db', mock_db):
            result = main.save_profile_info("12345", '{"weight": "75kg", "city": "York"}')
            self.assertIn("saved successfully", result)
            mock_db.save_profile_data.assert_called_once()

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_save_profile_info_invalid_json(self, mock_db_conn, mock_groq):
        """Test save_profile_info handles invalid JSON gracefully."""
        import main

        mock_db = Mock()

        with patch.object(main, 'db', mock_db):
            result = main.save_profile_info("12345", "not valid json")
            self.assertIn("Error", result)
            mock_db.save_profile_data.assert_not_called()

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_system_prompt_includes_forget_instruction(self, mock_db_conn, mock_groq):
        """Verify system prompt includes instruction for user to request deletion."""
        import main

        self.assertIn("forget", main.SYSTEM_PROMPT.lower())
        self.assertIn("delete", main.SYSTEM_PROMPT.lower())


class TestProfileDisplay(unittest.TestCase):
    """Tests for the /profile command display."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_show_profile_uses_html_bold(self, mock_db_conn, mock_groq):
        """Verify that show_profile uses HTML <b> tags, not Markdown ** bold."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": True, "city": "York"}

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update()
            context = self._create_mock_context()

            asyncio.run(main.show_profile(update, context))

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            text = call_args[0][0]

            # Should use HTML bold, not markdown
            self.assertIn("<b>PROFILE:</b>", text)
            self.assertNotIn("**PROFILE:**", text)
            # Should use HTML parse mode
            self.assertEqual(call_args[1].get('parse_mode'), "HTML")

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_show_profile_empty(self, mock_db_conn, mock_groq):
        """Test /profile when profile has only is_allowed (no other data)."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": True}

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update()
            context = self._create_mock_context()

            asyncio.run(main.show_profile(update, context))

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            text = call_args[0][0]
            # Should display profile data (not empty message, since is_allowed is set)
            self.assertIn("<b>PROFILE:</b>", text)

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_show_profile_unauthorized(self, mock_db_conn, mock_groq):
        """Test /profile for unauthorized user shows locked message."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {"is_allowed": False}

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update()
            context = self._create_mock_context()

            asyncio.run(main.show_profile(update, context))

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            # Should show locked message with HTML parse mode
            self.assertEqual(call_args[1].get('parse_mode'), "HTML")

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_show_profile_no_message(self, mock_db_conn, mock_groq):
        """Test /profile handler when update has no message."""
        import main

        mock_db = Mock()

        with patch.object(main, 'db', mock_db):
            update = Mock(spec=Update)
            update.message = None
            context = self._create_mock_context()

            asyncio.run(main.show_profile(update, context))

            mock_db.get_profile.assert_not_called()

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_show_profile_contains_json(self, mock_db_conn, mock_groq):
        """Test /profile displays profile data as formatted JSON."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {
            "is_allowed": True,
            "city": "York",
            "weight": "75kg"
        }

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update()
            context = self._create_mock_context()

            asyncio.run(main.show_profile(update, context))

            call_args = update.message.reply_text.call_args
            text = call_args[0][0]
            self.assertIn("York", text)
            self.assertIn("75kg", text)
            self.assertIn("<pre>", text)

    def _create_mock_update(self):
        """Helper to create a mock Update object."""
        update = Mock(spec=Update)
        message = AsyncMock(spec=Message)
        chat = Mock(spec=Chat)

        message.chat = chat
        chat.id = 12345
        message.chat_id = 12345
        message.reply_text = AsyncMock()

        update.message = message
        return update

    def _create_mock_context(self):
        """Helper to create a mock context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        return context


class TestAgentCycleToolExecution(unittest.TestCase):
    """Tests for the agent cycle tool calling behavior."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_agent_cycle_returns_response(self, mock_db_conn, mock_groq):
        """Test that run_agent_cycle returns LLM response text."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Hello, athlete!"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            result = main.run_agent_cycle("12345", "Hi")
            self.assertEqual(result, "Hello, athlete!")

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_agent_cycle_handles_llm_error(self, mock_db_conn, mock_groq):
        """Test that run_agent_cycle handles LLM errors gracefully."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {}
        mock_db.update_history = Mock()

        mock_llm = Mock()
        mock_llm.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            result = main.run_agent_cycle("12345", "Hi")
            self.assertIn("technical glitch", result.lower())

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_agent_cycle_strava_status_shown(self, mock_db_conn, mock_groq):
        """Test that Strava connection status is included in system prompt."""
        import main

        mock_db = Mock()
        mock_db.get_history.return_value = []
        mock_db.get_profile.return_value = {"is_allowed": True}
        mock_db.get_strava_tokens.return_value = {"access_token": "test"}
        mock_db.update_history = Mock()

        mock_response = Mock()
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "Response"
        mock_response.choices = [Mock(message=mock_message)]

        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response

        with patch.object(main, 'db', mock_db), \
             patch.object(main, 'client_llm', mock_llm):
            main.run_agent_cycle("12345", "Test")

            call_args = mock_llm.chat.completions.create.call_args
            messages = call_args[1]['messages'] if 'messages' in call_args[1] else call_args[0][0]
            system_msg = messages[0]['content']
            self.assertIn("CONNECTED", system_msg)


class TestHandleMessage(unittest.TestCase):
    """Tests for the handle_message function."""

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_message_invite_code_correct(self, mock_db_conn, mock_groq):
        """Test that correct invite code grants access."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {}
        mock_db.save_profile_data = Mock()

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update("RockyBalboa2026")
            context = self._create_mock_context()

            asyncio.run(main.handle_message(update, context))

            # Should save is_allowed: True
            mock_db.save_profile_data.assert_called_once_with(
                "12345", {"is_allowed": True}
            )
            # Should send success message
            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            self.assertIn("Access Granted", call_args[0][0])

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_message_invite_code_wrong(self, mock_db_conn, mock_groq):
        """Test that wrong invite code shows locked message."""
        import main

        mock_db = Mock()
        mock_db.get_profile.return_value = {}

        with patch.object(main, 'db', mock_db):
            update = self._create_mock_update("WrongPassword")
            context = self._create_mock_context()

            asyncio.run(main.handle_message(update, context))

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            self.assertEqual(call_args[1].get('parse_mode'), "HTML")

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_message_no_message(self, mock_db_conn, mock_groq):
        """Test handle_message with no message in update."""
        import main

        mock_db = Mock()

        with patch.object(main, 'db', mock_db):
            update = Mock(spec=Update)
            update.message = None
            context = self._create_mock_context()

            asyncio.run(main.handle_message(update, context))
            mock_db.get_profile.assert_not_called()

    @patch.dict(os.environ, test_env)
    @patch('transcription_service.Groq')
    @patch('psycopg2.connect')
    def test_handle_message_no_text(self, mock_db_conn, mock_groq):
        """Test handle_message with message but no text."""
        import main

        mock_db = Mock()

        with patch.object(main, 'db', mock_db):
            update = Mock(spec=Update)
            update.message = AsyncMock(spec=Message)
            update.message.text = None
            context = self._create_mock_context()

            asyncio.run(main.handle_message(update, context))
            mock_db.get_profile.assert_not_called()

    def _create_mock_update(self, text):
        """Helper to create a mock Update object with text."""
        update = Mock(spec=Update)
        message = AsyncMock(spec=Message)
        chat = Mock(spec=Chat)

        message.chat = chat
        chat.id = 12345
        message.chat_id = 12345
        message.text = text
        message.reply_text = AsyncMock()
        message.chat.send_action = AsyncMock()

        update.message = message
        return update

    def _create_mock_context(self):
        """Helper to create a mock context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        return context


if __name__ == '__main__':
    unittest.main()
