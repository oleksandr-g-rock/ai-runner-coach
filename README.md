# 🏅 ActiveBuddy: AI Sports Coach (Telegram Bot)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API-blue)
![OpenAI Lib](https://img.shields.io/badge/OpenAI-SDK-green)
![Strava](https://img.shields.io/badge/Strava-Powered-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![AI Agent](https://img.shields.io/badge/Type-Agentic_Application-purple)

A smart, **AI-powered personal coach** for **Athletes of All Disciplines** that lives in Telegram.

It integrates with **Strava** to analyze **ANY activity** (Run, Ride, Weight Training, Ski, Hike, Yoga, etc.), tracks your athlete profile, checks real-time weather, and provides personalized training advice with a touch of "Rocky Balboa" motivation.

Built with **Python (Aiohttp)**, **PostgreSQL**, and **LLMs** orchestrated via the standard **`openai` python library** (connecting to OpenRouter) using a robust **Webhook architecture**.

## 🤖 Why is this an Agentic App?

This is not a standard chatbot with hardcoded responses. It is an **Autonomous Agent** powered by Function Calling (Tool Use).

When you send a message, the LLM doesn't just reply; it **thinks** and decides which tools to execute:
* **Decides to check context:** If you ask "Should I go for a hike today?", it autonomously calls `check_weather(city)` and `check_strava(history)` before answering.
* **Decides to save memories:** If you say "My knee hurts after squats", it calls `save_profile_info(data)` to update its long-term memory in PostgreSQL.
* **Decides to talk:** If you just say "Hi", it replies directly without invoking tools.

It acts as a reasoning engine that bridges natural language with external APIs (Strava, Open-Meteo).

## ✨ Features

* **🧠 Universal Coaching:** Uses Llama 3.3 to analyze your specific context—whether you are training for a Marathon, building muscle in the Gym, or enjoying a Ski trip.
* **🔌 Standardized AI Integration:** Built on top of the standard `from openai import OpenAI` client. This ensures high compatibility and makes it easy to switch between OpenRouter, official OpenAI, or other compatible providers.
* **🏅 Full Strava Integration:** Connects via OAuth to fetch and analyze **Any activity type** supported by Strava (not just running/cycling, but also Weight Training, Yoga, Crossfit, etc.).
* **💾 Long-term Memory:** Remembers your age, weight, injuries, PRs, and goals (stored in PostgreSQL).
* **🌤 Weather Awareness:** Automatically checks weather conditions (wind, rain, temp) for your city before suggesting an outdoor workout.
* **🗣 Voice Support:** Transcribes voice messages using OpenAI Whisper (or compatible API)—perfect for post-workout notes.
* **⚡ Webhook Architecture:** Fast, efficient, and serverless-ready (no polling).
* **🔒 Private Mode:** Includes an "Invite Code" system to restrict access to authorized users only.

## 🏗 Architecture

The bot runs as a web server (`aiohttp`) that listens for Telegram Webhooks.

1.  **User** sends a message -> **Telegram** sends a POST request to the Bot.
2.  **Bot** authenticates user (checks DB & Invite Code).
3.  **Bot** processes intent (Talk, Check Strava, Update Profile).
4.  **Bot** initializes the `OpenAI` client (pointing to OpenRouter) to decide on tool usage.
5.  **Bot** calls external tools (Open-Meteo, Strava API).
6.  **Bot** replies asynchronously.

## 🚀 Deployment (Coolify / Docker)

This project is designed to be easily deployed using **Coolify** or any Docker-based environment.

### Prerequisites

* A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather)).
* A **Strava API Application** (from [Strava Settings](https://www.strava.com/settings/api)).
* An **OpenRouter API Key** (for LLM access).
* A **PostgreSQL Database**.
* A domain with HTTPS (required for Webhooks).

### Environment Variables

Set the following variables in your deployment environment (e.g., Coolify or `.env` file):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | Your Telegram Bot Token | `12345:ABC...` |
| `OPENROUTER_API_KEY` | Key for LLM access | `sk-or-v1-...` |
| `DATABASE_URL` | PostgreSQL Connection String | `postgres://user:pass@host:5432/db` |
| `STRAVA_CLIENT_ID` | Strava App Client ID | `123456` |
| `STRAVA_CLIENT_SECRET` | Strava App Client Secret | `abc12345...` |
| `BASE_URL` | **HTTPS** URL of your deployed bot | `https://my-bot.com` |
| `INVITE_CODE` | Password for new users | `RockyBalboa2026` |
| `WHISPER_API_URL` | URL for Whisper STT API | `http://whisper:8000/v1` |

### 🛠 Local Development

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/oleksandr-g-rock/ai-runner-coach.git](https://github.com/oleksandr-g-rock/ai-runner-coach.git)
    cd ai-runner-coach
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment:**
    Create a `.env` file and fill in the variables listed above.

4.  **Run the bot:**
    ```bash
    python main.py
    ```
    *Note: For local development with webhooks, you will need a tunnel like `ngrok` to expose your localhost to the internet.*

## 🔗 Strava Setup

To make Strava login work:
1.  Go to [Strava API Settings](https://www.strava.com/settings/api).
2.  Set the **Authorization Callback Domain** to the domain of your deployed bot (e.g., `ai-coach.your-domain.com`).

## 🛡 Security (Invite System)

By default, the bot is **locked**.
1.  New users see a "Business Card" message with links to this repo.
2.  To gain access, they must send the **Invite Code** (set in `INVITE_CODE` env var) as a message.
3.  Once authorized, their ID is whitelisted in the database permanently.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 📚 Detailed Features, Use Cases & FAQ
*Below is a comprehensive list of capabilities, supported scenarios, and technical details to help users and developers find this project.*

### 🏃 For Runners & Endurance Athletes
* **Marathon Training AI:** Generate personalized training schedules for 42km races based on your current Strava fitness level.
* **Couch to 5K & 10K:** Beginner-friendly coaching to get you from walking to running your first race.
* **Pace & Heart Rate Analysis:** The bot analyzes your splits, heart rate zones (Zone 2 training), and cadence to suggest improvements.
* **Injury Prevention:** Ask "My shin hurts, what should I do?" and get advice on recovery, foam rolling, and rest days.
* **Race Strategy:** Get tailored advice for pacing strategies (negative splits) for Half-Marathons and Ultras.
* **Virtual Running Coach:** A free alternative to expensive personal coaching or paid apps like Runna or TrainingPeaks.
* **Weather-Adaptive Training:** Checks wind, rain, and temperature to advise if you should run outside or hit the treadmill.

### 🚴 For Cyclists & Triathletes
* **Cycling Power Analysis:** Upload rides to analyze wattage, FTP (Functional Threshold Power) estimations, and endurance rides.
* **Triathlon Prep:** Supports multi-sport analysis including swim, bike, and run sessions (Ironman & 70.3 training insights).
* **Indoor vs Outdoor:** Guidance for Zwift sessions versus road cycling based on weather conditions.
* **Equipment Advice:** Ask the bot about gear maintenance, tire pressure, or nutrition for long rides.

### 🏋️ Gym, Crossfit & General Fitness
* **Strength Training for Runners:** Get advice on leg workouts, core stability, and plyometrics to improve running economy.
* **Weightlifting Logs:** The bot understands "I squatted 100kg for 5 reps" and tracks your PRs (Personal Records).
* **Calisthenics & Yoga:** Integration of recovery workouts and flexibility routines into your weekly schedule.
* **Hybrid Athlete:** optimize your week for both lifting heavy and running fast without overtraining.

### 💻 For Developers & AI Engineers (Tech Stack)
* **Python Telegram Bot Template:** A production-ready boilerplate using `aiohttp` and Webhooks (no polling).
* **AI Agent Architecture:** A clean example of building **Autonomous Agents** that use tools (Function Calling) before answering.
* **OpenAI & Llama 3 Integration:** Source code demonstrating how to switch between OpenAI GPT-4o, Claude 3.5 Sonnet, and Meta Llama 3 via OpenRouter.
* **PostgreSQL with Python:** Robust database design for storing user context, memory, and athletic history.
* **Voice-to-Text AI:** Implementation of OpenAI Whisper for processing voice notes from tired athletes.
* **Strava API OAuth 2.0:** Complete implementation of the Strava authentication flow and token refreshing mechanism.
* **Docker & Coolify:** Ready-to-deploy `Dockerfile` for hosting on VPS, DigitalOcean, or Coolify instances.

### ❓ Common Questions Solved (FAQ)
* "How to analyze Strava activities with AI?"
* "Is there a free AI running coach for Telegram?"
* "Telegram bot that checks weather for running."
* "Source code for Strava integration with Python."
* "How to build an LLM agent with memory?"
* "Self-hosted AI coach for privacy."

### 🇺🇦 UA / Ukrainian Description (Для українських користувачів)
* **AI Тренер з бігу:** Ваш персональний тренер у Telegram, який розмовляє українською.
* **Аналіз Strava:** Бот автоматично завантажує ваші пробіжки, велозаїзди та тренування, щоб дати поради.
* **План тренувань:** Складання планів на марафон, півмарафон, 10 км або схуднення.
* **Мотивація та дисципліна:** Бот нагадує про тренування та підтримує у стилі Роккі Бальбоа.
* **Безкоштовний аналог:** Заміна платним підпискам, доступна кожному.
* **Український розробник:** Проєкт створено в UK для підтримки спільноти бігунів.

---
*Keywords: AI Coach, Strava Bot, Running App, Python Agent, Telegram Bot, Workout Tracker, Gym Log, Llama 3, OpenRouter, Fitness Tech, Open Source Sports, Automated Coaching.*
