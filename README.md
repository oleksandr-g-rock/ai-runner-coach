# 🏅 ActiveBuddy — AI Sports Coach for Telegram

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Strava-Powered-FC4C02?style=for-the-badge&logo=strava&logoColor=white" alt="Strava"/>
  <img src="https://img.shields.io/badge/AI-Agentic_App-8B5CF6?style=for-the-badge&logo=openai&logoColor=white" alt="AI Agent"/>
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <b>Your personal AI-powered coach for running, cycling, gym, and every sport on Strava.</b><br/>
  Built with Python, PostgreSQL, and LLMs — deployed via Docker in minutes.
</p>

---

## ⚡ What is ActiveBuddy?

ActiveBuddy is a **Telegram bot** that acts as your personal sports coach. It connects to **Strava**, understands your training history, checks the **weather**, and gives you personalized advice — all through natural conversation.

> 💬 *"Should I run today?"*
> The bot checks your Strava history, looks at the weather in your city, considers your injuries and goals, and gives you a real answer.

### 🤖 Why is this an Agentic App?

This is **not** a chatbot with hardcoded responses. It's an **Autonomous Agent** powered by Function Calling (Tool Use).

| You say | The bot thinks | The bot does |
|---|---|---|
| *"Should I go for a hike today?"* | Needs weather + recent activity data | Calls `check_weather()` → `check_strava()` → responds |
| *"My knee hurts after squats"* | New health fact to remember | Calls `save_profile_info()` → confirms what was saved |
| *"Hi!"* | Just a greeting | Responds directly, no tools needed |

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **Universal Coaching** | Advice for running, cycling, gym, swimming, hiking, skiing — any Strava activity |
| 🏅 **Strava Integration** | OAuth connection to analyze your real training data (all activity types) |
| 💾 **Long-term Memory** | Remembers your age, weight, injuries, PRs, goals (stored in PostgreSQL) |
| ⏰ **Time Awareness** | Knows the current date/time — correctly understands "yesterday" and "last week" |
| 🌤 **Weather Awareness** | Checks conditions before suggesting outdoor workouts |
| 🗣 **Voice Messages** | Transcribes voice notes via Groq Whisper (Ukrainian, English, auto-detect) |
| ⚡ **Webhook Architecture** | Fast, production-ready — no polling |
| 🔒 **Invite System** | Private mode with access codes for authorized users only |

---

## 🏗 Architecture

```
User → Telegram → Webhook (POST /telegram)
                       │
                       ▼
              ┌─────────────────┐
              │  Access Check    │  (Invite Code / DB)
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Agent Cycle     │  LLM decides which tools to call
              │  (Llama 3.3)    │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    check_strava  check_weather  save_profile_info
     (Strava API)  (Open-Meteo)   (PostgreSQL)
```

**Tech Stack:** Python 3.11+ · aiohttp · PostgreSQL (JSONB) · OpenRouter (Llama 3.3) · Groq Whisper · Strava API

---

## 🚀 Quick Start

### Prerequisites

- [Telegram Bot Token](https://t.me/BotFather) 
- [Strava API Application](https://www.strava.com/settings/api)
- [OpenRouter API Key](https://openrouter.ai/)
- PostgreSQL Database
- HTTPS domain (for webhooks)

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `TELEGRAM_TOKEN` | Telegram Bot Token | `12345:ABC...` |
| `OPENROUTER_API_KEY` | LLM access key | `sk-or-v1-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |
| `STRAVA_CLIENT_ID` | Strava App Client ID | `123456` |
| `STRAVA_CLIENT_SECRET` | Strava App Client Secret | `abc12345...` |
| `BASE_URL` | HTTPS URL of the deployed bot | `https://my-bot.com` |
| `INVITE_CODE` | Access password for new users | `RockyBalboa2026` |
| `GROQ_WHISPER_API_KEY` | Groq API Key for voice transcription | `gsk_...` |
| `AGENT_MODEL` | LLM model name (optional) | `meta-llama/llama-3.3-70b-instruct:free` |
| `TOKEN_AI` | Max tokens for AI response (optional) | `1000` |

### 🛠 Local Development

```bash
# Clone the repository
git clone https://github.com/oleksandr-g-rock/ai-runner-coach.git
cd ai-runner-coach

# Install dependencies
pip install -r requirements.txt

# Set up environment (create .env file with variables above)

# Run the bot
python main.py
```

> **Note:** For local development with webhooks, use a tunnel like [ngrok](https://ngrok.com/) to expose localhost.

### 🐳 Docker

```bash
docker build -t activebuddy .
docker run -p 8080:8080 --env-file .env activebuddy
```

---

## 🧪 Running Tests

```bash
pip install pytest
python -m pytest -v
```

---

## 🔗 Strava Setup

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Set **Authorization Callback Domain** to your bot's domain (e.g., `ai-coach.your-domain.com`)
3. Users connect via the `/connect_strava` command in the bot

## 🛡 Security (Invite System)

1. New users see a welcome message with a link to this repo
2. To get access, they send the **Invite Code** (set via `INVITE_CODE` env var)
3. Once authorized, their ID is whitelisted in the database permanently

---

## 📂 Project Structure

```
ai-runner-coach/
├── main.py                        # Core bot logic (agent, handlers, DB)
├── transcription_service.py       # Groq Whisper voice transcription
├── test_main_integration.py       # Voice handling integration tests
├── test_bot_features.py           # Memory, profile, temporal context tests
├── test_transcription_service.py  # Transcription service unit tests
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container configuration
├── README.md                      # This file
└── LICENSE                        # MIT License
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

<details>
<summary><b>📚 Detailed Use Cases & FAQ</b></summary>

### 🏃 For Runners & Endurance Athletes
- **Marathon Training AI** — Personalized schedules based on your Strava fitness level
- **Couch to 5K & 10K** — Beginner-friendly coaching from walking to your first race
- **Pace & Heart Rate Analysis** — Splits, HR zones, cadence insights
- **Injury Prevention** — Recovery advice, foam rolling, rest day recommendations
- **Race Strategy** — Pacing strategies (negative splits) for Half-Marathons and Ultras
- **Weather-Adaptive Training** — Outdoor vs treadmill decisions based on real conditions

### 🚴 For Cyclists & Triathletes
- **Cycling Power Analysis** — Wattage, FTP estimations, endurance ride feedback
- **Triathlon Prep** — Multi-sport analysis (swim, bike, run) for Ironman & 70.3
- **Indoor vs Outdoor** — Zwift vs road cycling based on weather
- **Equipment Advice** — Gear maintenance, tire pressure, nutrition for long rides

### 🏋️ Gym, Crossfit & General Fitness
- **Strength Training** — Leg workouts, core stability, plyometrics for runners
- **Weightlifting Logs** — PR tracking ("I squatted 100kg for 5 reps")
- **Recovery Workouts** — Calisthenics, yoga, flexibility routines
- **Hybrid Athlete** — Balance lifting and running without overtraining

### 💻 For Developers
- **Python Telegram Bot Template** — Production-ready with aiohttp + Webhooks
- **AI Agent Architecture** — Function Calling / Tool Use example
- **OpenAI & Llama 3 Integration** — Switch between providers via OpenRouter
- **PostgreSQL JSONB** — User context, memory, and athletic history storage
- **Voice-to-Text** — Groq Whisper implementation for voice notes
- **Strava OAuth 2.0** — Complete auth flow with token refresh
- **Docker & Coolify Ready** — One-command deployment

### ❓ FAQ
- *"How to analyze Strava activities with AI?"* — Connect Strava, then just ask
- *"Is there a free AI running coach?"* — Yes, self-host this bot
- *"How to build an LLM agent with memory?"* — Study this repo's agent cycle

### 🇺🇦 Для українських користувачів
- **AI Тренер** — Персональний тренер у Telegram, який розмовляє українською
- **Аналіз Strava** — Автоматичне завантаження пробіжок, велозаїздів та тренувань
- **План тренувань** — Плани на марафон, півмарафон, 10 км або схуднення
- **Мотивація** — Підтримка у стилі Роккі Бальбоа 🥊

</details>
