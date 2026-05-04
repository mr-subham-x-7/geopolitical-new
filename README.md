🌍 Geo News AI Bot

An automated AI-powered geopolitical news bot that collects updates from X (Twitter), filters them using AI, and posts clean news summaries to Telegram.

---

🚀 Features

- 📡 Fetches latest posts from selected X accounts
- 🧠 Uses Google Gemini AI to filter important geopolitical news
- 📰 Generates clean, professional news digest
- 🤖 Automatically posts to Telegram
- ⏰ Runs twice daily using GitHub Actions (no server needed)

---

🛠️ Tech Stack

- Python
- twscrape (X data scraping)
- Google Gemini API
- Telegram Bot API
- GitHub Actions (automation)

---

⚙️ Setup Guide

1. Clone Repository

git clone https://github.com/YOUR_USERNAME/geo-news-bot.git

2. Install Dependencies

pip install -r requirements.txt

3. Add Secrets (GitHub)

Go to:
Settings → Secrets → Actions

Add:

- X_USERNAME
- X_PASSWORD
- X_EMAIL
- GEMINI_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

---

▶️ Run Manually

Go to:
GitHub → Actions → Run Workflow

---

📅 Automation Schedule

- 8:00 AM IST
- 6:30 PM IST

---

📌 Example Output

🌍 GEOPOLITICAL INTEL DIGEST
📅 Daily Update

🔴 MAJOR GLOBAL EVENT

- Key detail
- Key detail
  ~ Source: @account

━━━━━━━━━━━━━━━━
📡 Monitored via GeoIntel Bot

---

⚠️ Notes

- Uses X scraping → may break if X changes system
- Keep API keys private
- Free tier limits apply

---

📈 Future Improvements

- Add Instagram / YouTube automation
- Improve AI filtering
- Add multi-language support

---

👨‍💻 Author

Built as a student project to learn AI automation & real-world systems.
