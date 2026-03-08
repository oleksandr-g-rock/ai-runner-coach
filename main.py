import os
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
import requests
import psycopg2
from psycopg2.extras import Json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from dotenv import load_dotenv
from aiohttp import web
from transcription_service import create_transcription_service

# ============================================================================
# 1. CONFIGURATION & SETUP
# ============================================================================
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
GROQ_WHISPER_API_KEY = os.environ.get("GROQ_WHISPER_API_KEY")

# --- PASSWORD CONFIG ---
# Default password if not set in env vars.
INVITE_CODE = os.environ.get("INVITE_CODE", "RockyBalboa2026")

# Strava Config
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

# Web Server Config
BASE_URL = os.environ.get("BASE_URL")
if BASE_URL and BASE_URL.endswith('/'):
    BASE_URL = BASE_URL[:-1]

REDIRECT_URI = f"{BASE_URL}/strava_callback"

AGENT_MODEL = os.environ.get("AGENT_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# Token Limit for AI Response (Controlled via Coolify)
TOKEN_AI = int(os.environ.get("TOKEN_AI", 1000))

# Topic filter: if set, the bot only responds to messages from this Telegram topic (thread) ID.
_topic_id_raw = os.environ.get("TOPIC_ID")
TOPIC_ID = int(_topic_id_raw) if _topic_id_raw else None

# LOCKED MODE MESSAGE (HTML FORMAT)
LOCKED_MESSAGE = (
    "👋 <b>Hello!</b> I am ActiveBuddy — your Personal AI Sports Coach.\n\n"
    "I am currently operating in <b>private mode</b> (invite only). 🔒\n\n"
    "💻 <b>Source Code:</b> <a href='https://github.com/oleksandr-g-rock/ai-runner-coach'>GitHub Repository</a>\n\n"
    "🔑 <b>Have an access code?</b> Just send it here as a message."
)

# SYSTEM PROMPT (ENGLISH - ADAPTIVE)
SYSTEM_PROMPT = (
    "You are ActiveBuddy, a personal AI sports coach. You help with ALL sports and physical activities supported by Strava."
    " You have access to the user's profile and data."
    "\n\nYOUR INSTRUCTIONS:"
    "\n1. **Strava:** If you see 'STRAVA: NOT CONNECTED' and the user asks for analysis, tell them to use /connect_strava."
    "\n2. **Memory (CRITICAL):** ONLY save facts directly related to sport, fitness, and health using `save_profile_info`."
    " Save: age, weight, height, city/location, injuries, PRs, race goals, training preferences, equipment, fitness level."
    " DO NOT save: casual conversations, social plans, food/drink mentions, concerts, entertainment, opinions, or everyday chat."
    " If the user explicitly asks you to forget or delete something, remove that key from the profile by saving it with an empty value."
    " Do not just say you saved it — actually use the tool. After calling `save_profile_info`, confirm what was saved."
    "\n3. **Weather:** To check weather, use the city stored in the profile. If no city is saved, ask the user."
    "\n4. **Analysis:** If the user asks for advice or a plan, use `check_weather` and `check_strava` tools. Analyze ANY activity type present in the history (Run, Ride, Swim, Ski, Hike, Weight Training, etc.)."
    "\n5. **Context:** Always consider profile data when giving advice (e.g., don't suggest a heavy leg workout if the user just did a hard hike or long ride)."
    "\n6. **Time Awareness (CRITICAL):** The current date and time are provided in the CURRENT DATE/TIME field below."
    " Use this to understand temporal context. Messages in the conversation history include timestamps — pay attention to them."
    " When the user says 'yesterday', 'last week', etc., interpret these relative to the CURRENT date/time, NOT relative to the last message."
    "\n7. **Language & Tone:** Your default language is **English**. However, **if the user speaks Ukrainian (or another language), reply in the user's language**. Be friendly, energetic, and concise."
    "\n8. **Persona:** You are a supportive partner. End with a short motivational quote (Rocky Balboa style)."
    "\n\nRESTRICTIONS:"
    "\n- Do not output technical tags (like <tool_code>)."
    "\n- Do not hallucinate data."
    "\n- Stop immediately after giving advice."
    "\n- **Formatting:** Do NOT use markdown bolding (asterisks like **text**). Telegram does not render them well inside code blocks or sometimes in general text. Use plain text and emojis only."
    "\n- **Safety:** Decline to answer requests related to illegal acts."
)

# ============================================================================
# 2. DATABASE (PostgreSQL)
# ============================================================================
class PostgresDB:
    def __init__(self, db_url):
        self.db_url = db_url
        self._init_db()

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def _init_db(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_data (
            chat_id VARCHAR(50) PRIMARY KEY,
            profile JSONB DEFAULT '{}'::jsonb,
            history JSONB DEFAULT '[]'::jsonb,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        alter_table_query = """
        ALTER TABLE user_data ADD COLUMN IF NOT EXISTS strava_auth JSONB DEFAULT '{}'::jsonb;
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_table_query)
                    cur.execute(alter_table_query) 
        except Exception as e:
            logger.error(f"DB Init Error: {e}")

    def get_history(self, chat_id):
        query = "SELECT history FROM user_data WHERE chat_id = %s"
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id),))
                    res = cur.fetchone()
                    return res[0] if res else []
        except Exception: return []

    def update_history(self, chat_id, history):
        query = """
        INSERT INTO user_data (chat_id, history, last_updated)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (chat_id) DO UPDATE SET history = EXCLUDED.history;
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id), Json(history)))
        except Exception as e: logger.error(f"DB History Error: {e}")

    def get_profile(self, chat_id):
        query = "SELECT profile FROM user_data WHERE chat_id = %s"
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id),))
                    res = cur.fetchone()
                    return res[0] if res else {}
        except Exception: return {}

    def save_profile_data(self, chat_id, new_data_dict):
        current = self.get_profile(chat_id)
        current.update(new_data_dict)
        query = """
        INSERT INTO user_data (chat_id, profile, last_updated)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (chat_id) DO UPDATE SET profile = EXCLUDED.profile;
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id), Json(current)))
            return True
        except Exception as e:
            logger.error(f"DB Profile Error: {e}")
            return False

    def save_strava_tokens(self, chat_id, tokens):
        query = """
        INSERT INTO user_data (chat_id, strava_auth, last_updated)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (chat_id) DO UPDATE SET strava_auth = EXCLUDED.strava_auth;
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id), Json(tokens)))
            return True
        except Exception as e:
            logger.error(f"DB Strava Save Error: {e}")
            return False

    def get_strava_tokens(self, chat_id):
        query = "SELECT strava_auth FROM user_data WHERE chat_id = %s"
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(chat_id),))
                    res = cur.fetchone()
                    return res[0] if res else {}
        except Exception: return {}

db = PostgresDB(DATABASE_URL)

# ============================================================================
# 3. TOOLS IMPLEMENTATION
# ============================================================================

def refresh_strava_token(chat_id, refresh_token):
    try:
        res = requests.post(
            'https://www.strava.com/oauth/token',
            data={
                'client_id': STRAVA_CLIENT_ID,
                'client_secret': STRAVA_CLIENT_SECRET,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }, timeout=10
        )
        if res.status_code == 200:
            new_tokens = res.json()
            db.save_strava_tokens(chat_id, new_tokens)
            return new_tokens['access_token']
        else:
            logger.error(f"Strava Refresh Failed: {res.text}")
    except Exception as e:
        logger.error(f"Strava Refresh Exception: {e}")
    return None

def check_strava(chat_id): 
    logger.info(f"🏃 AGENT: Checking Strava for {chat_id}...")
    
    tokens = db.get_strava_tokens(chat_id)
    if not tokens or 'access_token' not in tokens:
        return "STATUS: NOT CONNECTED. Tell the user to run /connect_strava"

    access_token = tokens['access_token']
    expires_at = tokens.get('expires_at', 0)
    refresh_token_val = tokens.get('refresh_token')

    if time.time() > (expires_at - 60):
        logger.info(f"Token expired for {chat_id}, refreshing...")
        access_token = refresh_strava_token(chat_id, refresh_token_val)
        if not access_token:
            return "ERROR: Token expired and refresh failed. Please reconnect Strava."

    try:
        after_ts = int(time.time()) - (7 * 86400)
        res = requests.get(
            'https://www.strava.com/api/v3/athlete/activities',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'after': after_ts, 'per_page': 40}, 
            timeout=10
        )
        
        if res.status_code == 401:
            return "ERROR: Strava Unauthorized. Try /connect_strava again."

        activities = res.json()
        
        if not activities: return "Strava: No activities found in the last 7 days."

        if isinstance(activities, dict) and 'message' in activities:
             return f"Strava Error: {activities['message']}"

        activities.sort(key=lambda x: x['start_date'], reverse=True)
        recent_activities = activities[:10] 

        summary = []
        for act in recent_activities:
            type_act = act.get('type', 'Activity')
            date = act.get('start_date_local', '')[:16].replace('T', ' ') 
            hr = act.get('average_heartrate', 'N/A')
            
            distance_meters = act.get('distance', 0)
            moving_time_seconds = act.get('moving_time', 0)
            
            m, s = divmod(moving_time_seconds, 60)
            h, m = divmod(m, 60)
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"

            if distance_meters > 0:
                dist_km = round(distance_meters / 1000, 2)
                stats = f"{dist_km}km in {time_str}"
            else:
                stats = f"Duration: {time_str}"

            summary.append(f"Date: {date}, Type: {type_act}, {stats}, HR: {hr}")
        
        return "Recent Activities (Newest First):\n" + "\n".join(summary)
    except Exception as e:
        return f"Strava Error: {str(e)}"

def check_weather(city_english):
    logger.info(f"🌦 AGENT: Checking weather for {city_english}...")
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search", 
            params={"name": city_english, "count": 1, "language": "en", "format": "json"}).json()
        if not geo.get("results"): return f"Error: City '{city_english}' not found."
        
        loc = geo["results"][0]
        w = requests.get("https://api.open-meteo.com/v1/forecast",
            params={"latitude": loc["latitude"], "longitude": loc["longitude"],
                    "current": "temperature_2m,weather_code,apparent_temperature"}).json()
        
        curr = w["current"]
        code = curr["weather_code"]
        desc = "Cloudy"
        if code == 0: desc = "Clear"
        elif code in [51, 53, 55, 61, 63]: desc = "Rain"
        elif code in [71, 73, 75]: desc = "Snow"
        
        return f"Weather in {loc['name']}: {desc}, Temp: {curr['temperature_2m']}C, Feels: {curr['apparent_temperature']}C"
    except Exception as e: return f"Weather Error: {str(e)}"

def save_profile_info(chat_id, info_json):
    logger.info(f"💾 AGENT: Saving profile for {chat_id}: {info_json}")
    try:
        data = json.loads(info_json)
        db.save_profile_data(chat_id, data)
        return "Profile information saved successfully."
    except Exception as e:
        return f"Error saving profile: {e}"

# ============================================================================
# 4. AGENT LOGIC
# ============================================================================
client_llm = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={"HTTP-Referer": "https://bot.local", "X-Title": "AgentCoach"}
)

# Initialize Groq transcription service
transcription_service = None
if GROQ_WHISPER_API_KEY:
    try:
        transcription_service = create_transcription_service()
        logger.info("✅ Groq transcription service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize transcription service: {e}")
else:
    logger.warning("GROQ_WHISPER_API_KEY not set, voice transcription will not work")

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "check_strava",
            "description": "Get recent activities from Strava.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_weather",
            "description": "Check the weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_english": {"type": "string", "description": "City name in English"}
                },
                "required": ["city_english"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_profile_info",
            "description": "Save sport, fitness, and health related facts about the user (e.g., age, weight, city, injuries, PRs, goals, equipment). Do NOT save casual or non-sport info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_json": {"type": "string", "description": "JSON string with sport/fitness related data to save."}
                },
                "required": ["info_json"]
            }
        }
    }
]

def run_agent_cycle(chat_id, user_text):
    chat_id = str(chat_id) 
    history = db.get_history(chat_id)
    profile = db.get_profile(chat_id)
    
    strava_tokens = db.get_strava_tokens(chat_id)
    strava_status = "CONNECTED ✅" if strava_tokens else "NOT CONNECTED ❌"

    now = datetime.now(timezone.utc)
    current_time_str = now.strftime("%Y-%m-%d %H:%M UTC")

    system_msg_content = SYSTEM_PROMPT
    system_msg_content += f"\n\nCURRENT DATE/TIME: {current_time_str}"
    system_msg_content += f"\nSTATUS STRAVA: {strava_status}"
    if profile:
        system_msg_content += f"\nCURRENT USER PROFILE:\n{json.dumps(profile, ensure_ascii=False)}"

    clean_history = []
    for m in history:
        if m["role"] in ["user", "assistant"] and m.get("content"):
            entry = {"role": m["role"], "content": m["content"]}
            if m.get("timestamp"):
                entry["content"] = f"[{m['timestamp']}] {m['content']}"
            clean_history.append(entry)
    clean_history = clean_history[-10:]

    messages = [{"role": "system", "content": system_msg_content}] + clean_history
    messages.append({"role": "user", "content": user_text})

    try:
        response = client_llm.chat.completions.create(
            model=AGENT_MODEL, 
            messages=messages, 
            tools=TOOLS_SCHEMA, 
            tool_choice="auto",
            max_tokens=TOKEN_AI  # Set token limit here
        )
        msg = response.choices[0].message
        
        if msg.tool_calls:
            logger.info(f"🤖 Agent calls {len(msg.tool_calls)} tools")
            messages.append(msg)

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool_result = "Error"
                
                if func_name == "check_strava":
                    tool_result = check_strava(chat_id)
                elif func_name == "check_weather":
                    city = args.get("city_english")
                    if not city: city = profile.get("location") or profile.get("city")
                    if not city: city = "Kyiv"
                    tool_result = check_weather(city)
                elif func_name == "save_profile_info":
                    tool_result = save_profile_info(chat_id, args.get("info_json", "{}"))
                
                messages.append({
                    "role": "tool", "content": tool_result, "tool_call_id": tool_call.id
                })

            final_res = client_llm.chat.completions.create(
                model=AGENT_MODEL, 
                messages=messages,
                max_tokens=TOKEN_AI  # Ensure final response also respects the limit
            )
            ai_text = final_res.choices[0].message.content
        else:
            ai_text = msg.content

    except Exception as e:
        logger.error(f"LLM Error: {e}")
        ai_text = "Sorry, technical glitch."

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    clean_history.append({"role": "user", "content": user_text, "timestamp": timestamp})
    clean_history.append({"role": "assistant", "content": ai_text, "timestamp": timestamp})
    db.update_history(chat_id, clean_history)

    return ai_text

# ============================================================================
# 5. WEB SERVER (HANDLERS)
# ============================================================================
async def strava_callback_handler(request):
    """Handles callback from Strava."""
    code = request.query.get('code')
    chat_id = request.query.get('state') 
    error = request.query.get('error')

    bot = request.app['bot']

    if error:
        if chat_id:
            await bot.send_message(chat_id=chat_id, text="❌ Authorization canceled.")
        return web.Response(text="Authorization Denied.")

    if not code or not chat_id:
        return web.Response(text="Error: Missing code or state.")

    try:
        res = requests.post(
            'https://www.strava.com/oauth/token',
            data={
                'client_id': STRAVA_CLIENT_ID,
                'client_secret': STRAVA_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            }, timeout=10
        )
        data = res.json()
        
        if 'access_token' in data:
            db.save_strava_tokens(chat_id, data)
            logger.info(f"✅ Strava connected for {chat_id}")
            await bot.send_message(chat_id=chat_id, text="✅ **Success!** Strava connected!", parse_mode="Markdown")
            return web.Response(text="Success! You can close this window.")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ Authorization error.")
            return web.Response(text=f"Auth Failed: {data}")
            
    except Exception as e:
        logger.error(f"Auth Exception: {e}")
        return web.Response(text="Internal Server Error.")

async def telegram_webhook_handler(request):
    """Handles incoming Telegram Webhook updates."""
    app = request.app['application']
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=500)

async def on_startup(web_app):
    """Starts the bot on server startup."""
    application = web_app['application']
    await application.initialize()
    await application.start()
    
    webhook_url = f"{BASE_URL}/telegram"
    logger.info(f"🔗 Setting webhook to: {webhook_url}")
    await application.bot.set_webhook(url=webhook_url)

async def on_shutdown(web_app):
    """Stops the bot on server shutdown."""
    application = web_app['application']
    await application.stop()
    await application.shutdown()

# ============================================================================
# 6. BOT HANDLERS & COMMANDS
# ============================================================================

def _is_allowed_topic(message) -> bool:
    """Return True if the message belongs to the configured topic (or no topic filter is set)."""
    if TOPIC_ID is None:
        return True
    return getattr(message, 'message_thread_id', None) == TOPIC_ID

async def connect_strava_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore technical updates
    if not update.message: return
    if not _is_allowed_topic(update.message): return

    chat_id = str(update.message.chat_id)

    # --- ACCESS CHECK ---
    profile = db.get_profile(chat_id)
    if not profile.get("is_allowed"):
        await update.message.reply_text(LOCKED_MESSAGE, parse_mode="HTML")
        return
    # --------------------

    if not STRAVA_CLIENT_ID or not REDIRECT_URI:
        await update.message.reply_text("❌ Configuration Error.")
        return

    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope=activity:read_all"
        f"&state={chat_id}" 
    )
    keyboard = [[InlineKeyboardButton("🔗 Login with Strava", url=auth_url)]]
    await update.message.reply_text(
        "Please authorize Strava access (read-only).",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if not _is_allowed_topic(update.message): return

    chat_id = str(update.message.chat_id)

    # --- ACCESS CHECK ---
    profile = db.get_profile(chat_id)
    if not profile.get("is_allowed"):
        await update.message.reply_text(LOCKED_MESSAGE, parse_mode="HTML")
        return
    # --------------------

    await update.message.reply_text("👋 Hi! I'm ActiveBuddy.\nPress /connect_strava to link your activities (Run, Ride, Swim, etc.).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Ignore technical updates (no text)
    if not update.message or not update.message.text:
        return
    if not _is_allowed_topic(update.message): return

    chat_id = str(update.message.chat_id)
    user_text = update.message.text
    
    profile = db.get_profile(chat_id)
    
    # 2. CHECK ACCESS (INVITE CODE)
    if not profile.get("is_allowed"):
        # Check password
        if user_text.strip() == INVITE_CODE:
            # PASSWORD CORRECT
            db.save_profile_data(chat_id, {"is_allowed": True})
            await update.message.reply_text(
                "🥊 <b>Access Granted!</b> Welcome to the club.\n\nI am your personal coach now. Start with /connect_strava or just tell me about your goals.",
                parse_mode="HTML"
            )
            return
        else:
            # PASSWORD INCORRECT
            await update.message.reply_text(LOCKED_MESSAGE, parse_mode="HTML")
            return

    # 3. ACCESS GRANTED - RUN LOGIC
    await update.message.chat.send_action("typing")
    response = await asyncio.to_thread(run_agent_cycle, update.message.chat_id, user_text)
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if not _is_allowed_topic(update.message): return

    chat_id = str(update.message.chat_id)

    # --- ACCESS CHECK ---
    profile = db.get_profile(chat_id)
    if not profile.get("is_allowed"):
        await update.message.reply_text("🔒 Please enter the text password first.")
        return
    # --------------------

    # Check if transcription service is available
    if not transcription_service:
        await update.message.reply_text("❌ Voice transcription is not configured.")
        return

    status = await update.message.reply_text("👂 Listening...")
    temp_file = f"voice_{update.message.voice.file_id}.ogg"
    try:
        new_file = await context.bot.get_file(update.message.voice.file_id)
        await new_file.download_to_drive(temp_file)
        
        # Transcribe using Groq
        def transcribe():
            return transcription_service.transcribe_audio(temp_file)
        
        text = await asyncio.to_thread(transcribe)
        await status.edit_text(f"🗣 <i>\"{text}\"</i>", parse_mode="HTML")
        await update.message.chat.send_action("typing")
        response = await asyncio.to_thread(run_agent_cycle, update.message.chat_id, text)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        await status.edit_text("❌ Error processing voice message. Please try again or contact support if the issue persists.")
    finally:
        if os.path.exists(temp_file): os.remove(temp_file)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if not _is_allowed_topic(update.message): return
    chat_id = str(update.message.chat_id)
    
    # --- ACCESS CHECK ---
    profile = db.get_profile(chat_id)
    if not profile.get("is_allowed"):
        await update.message.reply_text(LOCKED_MESSAGE, parse_mode="HTML")
        return
    # --------------------

    if not profile:
        await update.message.reply_text("🤷‍♂️ Profile is empty.")
    else:
        formatted_json = json.dumps(profile, indent=2, ensure_ascii=False)
        await update.message.reply_text(f"📂 <b>PROFILE:</b>\n<pre>{formatted_json}</pre>", parse_mode="HTML")

async def show_last_strava(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if not _is_allowed_topic(update.message): return
    chat_id = str(update.message.chat_id)

    # --- ACCESS CHECK ---
    profile = db.get_profile(chat_id)
    if not profile.get("is_allowed"):
        await update.message.reply_text(LOCKED_MESSAGE, parse_mode="HTML")
        return
    # --------------------

    await update.message.reply_text("🔄 Checking Strava...")
    response_text = await asyncio.to_thread(check_strava, chat_id)
    await update.message.reply_text(response_text)

# ============================================================================
# MAIN
# ============================================================================
async def main():
    logger.info("🚀 STARTING WEBHOOK MODE...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("connect_strava", connect_strava_command)) 
    application.add_handler(CommandHandler("strava", show_last_strava))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    web_app = web.Application()
    web_app['application'] = application
    web_app['bot'] = application.bot

    web_app.router.add_get('/strava_callback', strava_callback_handler) 
    web_app.router.add_post('/telegram', telegram_webhook_handler)

    web_app.on_startup.append(on_startup)
    web_app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(web_app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    logger.info(f"🌍 Webhook Server running on port 8080. Base URL: {BASE_URL}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
