# Mindo — Mental Health Support Platform

A Flask-based mental health support platform combining an AI chatbot, structured mental health & cognitive assessments, daily wellness tasks, a peer community/chat system, emotional analytics dashboard, and emergency support resources.

---

## Features

- 🔐 **Auth** — username/password login & registration (MySQL-backed)
- 🤖 **AI Mental Health Chatbot** — supportive, non-diagnostic chatbot powered by an LLM via OpenRouter, with basic crisis-keyword detection that surfaces helpline guidance
- 📝 **Mental health assessments** — multi-stage questionnaires scoring depression, anxiety, anger, and loneliness
- 🧠 **Cognitive function assessment** — a second questionnaire scoring cognitive function and classifying impairment level
- 📊 **Dashboard** — visualizes assessment history, cognitive status, emotional analysis, and daily task completion
- ✅ **Daily wellness tasks** — a checklist of self-care habits (meditation, hydration, gratitude, etc.) tracked per day
- 💬 **Chat rooms** — real-time messaging via Flask-SocketIO, with shareable room codes
- 👥 **Community** — browse members, post messages, and join community tasks/organizations
- 🚨 **Emergency support** — quick access to emergency contacts and an alert-sending endpoint
- 🗣️ **Feedback** — simple feedback submission page

---

## Tech Stack

- **Backend:** Flask, Flask-SocketIO
- **Database:** MySQL (`mysql-connector-python`)
- **AI Chatbot:** OpenRouter API (via `requests`) — model `openai/gpt-3.5-turbo`
- **Other AI libs present:** `google-generativeai`, `tensorflow` (imported for future/extended functionality — see [Notes](#notes))
- **Image handling:** Pillow (`PIL`)
- **Config:** `python-dotenv`

---

## Installation & Setup

**[Install Python]** https://www.python.org/downloads/

**[Install pip]**

```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
```

```bash
python3 get-pip.py
```

Ensure pip is installed by running the following command

```bash
pip --version
```

If you have Python & pip installed then check their version in the terminal or command line tools

```bash
python3 --version
```

```bash
pip --version
```

---

## Clone the Repository

```bash
git clone https://github.com/<your-username>/Mindo.git
cd Mindo
```

---

## Install Dependencies

```bash
pip install flask flask-socketio mysql-connector-python werkzeug pillow python-dotenv tensorflow requests google-generativeai
```

Or, if you maintain a `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## Database Setup

This app expects a local MySQL database named `mindo` (or `mindot`, per the queries in `app.py`). At minimum, create tables for:

- `mindot` — user accounts (`username`, `password`, `name`, `email`, `Gender`, `Age`, `Profession`)
- `response` — mental health assessment answers + scores (`Q1`–`Q10`, `depression_score`, `anxiety_score`, `anger_score`, `loneliness_score`, `timestamp`)
- `response21` — cognitive assessment results (`cognitive_function_score`, `cognitive_status`, `timestamp`)
- `response3` — emotional analysis responses (`Q1`–`Q5`)
- `dailytask` — daily task checklist (`T1`–`T7`, `task_date`, `timestamp`)
- `community` — community task/organization sign-ups (`username`, `task`, `organization`)
- `chat_messages` — direct messages (`sender`, `receiver`/`recipient`, `message`, `created_at`)

```sql
CREATE DATABASE mindo;
```

> Update table/column names or add migrations as needed — the app currently expects these tables to already exist.

---

## Environment Variables

Create a `.env` file in the project root and **never commit it**:

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=mindo
FLASK_SECRET_KEY=generate_a_strong_random_secret
```

Update `get_db_connection()` and the `OPENROUTER_API_KEY` reference in `app.py` to read from these environment variables via `os.getenv(...)` instead of being hardcoded.

---

## Usage

```bash
python3 app.py
```

The app runs with Flask-SocketIO on `http://127.0.0.1:5000` by default.

### Typical Flow

1. Register an account and log in
2. Land on the chat/home page, where you can talk to the AI mental health assistant
3. Complete the mental health and cognitive assessments (`/mental_health`, `/assessment2`, `/assessment3`)
4. Check your **Dashboard** for scored results, emotional analysis, and daily task progress
5. Complete daily wellness tasks (`/daily_tasks`)
6. Join or start real-time chat rooms, or engage with the **Community** page
7. Use the **Emergency** page for quick access to support contacts if needed

---

## Project Structure (expected)

```
Mindo/
├── app.py                  # Main Flask app (routes, chatbot, assessments, dashboard)
├── templates/
│   ├── home1.html / room1.html      # Chat room UI
│   ├── login.html / register.html
│   ├── chat1.html                     # AI chatbot UI
│   ├── mental_health.html / assessment2.html / assessment3.html
│   ├── dashboard.html
│   ├── daily_tasks.html
│   ├── community.html / members.html / chat_section.html
│   ├── profile.html / update_profile.html
│   ├── guidelines.html / feedback.html / emergency.html
│   └── suggestions.html / mental_health_success.html
├── .env                     # Secrets (not committed)
└── README.md
```

---

## Notes

- The chatbot's crisis-keyword detection is a **basic safety net**, not a substitute for real crisis intervention — consider integrating a proper crisis-response workflow and licensed helpline info for production use.
- `tensorflow` and `google-generativeai` are imported but not currently wired into any route in the provided code — likely reserved for a planned feature (e.g. image-based mood detection or an alternate chatbot backend).
- Passwords are currently compared in plaintext (`user["password"] == password`) — switch to hashed passwords (e.g. `werkzeug.security.generate_password_hash` / `check_password_hash`) before any real deployment.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a PR

---

## License

This project is licensed under the MIT License.
