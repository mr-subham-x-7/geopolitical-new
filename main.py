import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from twscrape import API, gather
import google.generativeai as genai
from telegram import Bot

# ─── CONFIG ───────────────────────────────────────────────────────────────────

ACCOUNTS_TO_MONITOR = [
    # 🌍 Global Intel
    "Reuters", "KyivPost", "spectatorindex", "BBCWorld", "CNN",
    "duandang", "ELINTNews", "Global_Mil_Info", "Osinttechnical",
    "sentdefender", "The_IntelHub", "detresfa_", "thewarzonewire",
    "OdishaWeather7", "usd0705",
    # 🇮🇳 India Focused
    "JaipurDialogues", "OpIndia_com", "MeghUpdates", "AdityaRajKaul",
    "NewsAlgebraIND", "IndianInfoGuid", "IndianTechGuide", "srijanpalsingh"
]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

# ─── AI FILTER ────────────────────────────────────────────────────────────────

def analyze_tweet(text: str):
    prompt = f"""
You are a geopolitical intelligence analyst for "Geopol Buddy",
an India-focused Telegram intel channel.

Strictly analyze this tweet.

Focus areas:
- India geopolitics & internal security
- China-India relations & border tensions
- Russia-India defense & trade deals
- China-Taiwan tensions
- Middle East conflicts
- Global power shifts
- Military & defense developments
- International sanctions
- South East Asia strategic developments
- India regional state affairs & projects
- International relations & diplomacy

STRICTLY IGNORE:
- Personal opinions without hard facts
- Propaganda or heavy bias
- Memes, jokes, sarcasm
- Ads or promotions
- Reposts without new information
- Local news with zero strategic value

If HIGH VALUE — return EXACTLY this format:
PRIORITY: HIGH or MEDIUM or LOW
SUMMARY: (2 sharp factual lines)
IMPACT ON INDIA: (1-2 lines, only if directly relevant)

If NOT valuable — return exactly: SKIP

Tweet:
{text}
"""
    try:
        response = gemini.generate_content(prompt)
        if not response or not response.text:
            return None
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return None

# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def safe_send(bot: Bot, text: str, **kwargs):
    """Auto-split and send messages safely within Telegram 4000 char limit."""
    text = text.strip()
    while len(text) > 4000:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text[:4000],
            **kwargs
        )
        await asyncio.sleep(1)
        text = text[4000:]
    if text:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            **kwargs
        )

async def send_tweet(bot: Bot, item: dict, label: str = ""):
    """Send a single analyzed tweet. Attach image if available."""
    msg = f"{label}\n{item['text']}\n\n🔗 {item['link']}"
    if item["has_video"]:
        msg += "\n🎥 *Video: tap link above to watch*"

    if item["has_photo"] and item["photo_url"]:
        try:
            await bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=item["photo_url"],
                caption=msg[:1024],
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            print(f"⚠️ Photo failed, sending as text: {e}")

    await safe_send(bot, msg, parse_mode="Markdown", disable_web_page_preview=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    print("🚀 Geopol Buddy Starting...\n")

    # ── Validate secrets ──
    secrets = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID":   TELEGRAM_CHAT_ID,
        "GEMINI_API_KEY":     GEMINI_API_KEY,
        "X_USERNAME":         os.getenv("X_USERNAME"),
        "X_PASSWORD":         os.getenv("X_PASSWORD"),
        "X_EMAIL":            os.getenv("X_EMAIL"),
    }
    missing = [k for k, v in secrets.items() if not v]
    if missing:
        print(f"❌ Missing secrets: {', '.join(missing)}")
        return

    # ── Login to X ──
    print("🔐 Logging into X...")
    api = API()
    await api.pool.add_account(
        username=os.getenv("X_USERNAME"),
        password=os.getenv("X_PASSWORD"),
        email=os.getenv("X_EMAIL"),
        email_password=os.getenv("X_PASSWORD")
    )
    await api.pool.login_all()
    print("✅ X login successful\n")

    # ── Time window ──
    since   = datetime.now(timezone.utc) - timedelta(hours=6)
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    date_str = ist_now.strftime("%d %B %Y")
    time_str = ist_now.strftime("%I:%M %p")

    print(f"📡 Fetching tweets from last 6 hours...\n")

    # ── Fetch tweets ──
    grouped  = defaultdict(list)
    seen_ids = set()

    for acc in ACCOUNTS_TO_MONITOR:
    try:
        user = await api.user_by_login(acc)
        tweets = await gather(api.user_tweets(user.id, limit=15))
        count = 0
        for tweet in tweets:
            t_time = tweet.date
            if t_time.tzinfo is None:
                t_time = t_time.replace(tzinfo=timezone.utc)
            if t_time > since and tweet.id not in seen_ids:
                seen_ids.add(tweet.id)
                grouped[acc].append(tweet)
                count += 1
        print(f"  ✅ @{acc}: {count} tweets")
    except Exception as e:
        print(f"  ⚠️ @{acc} failed: {e}")

    total = sum(len(v) for v in grouped.values())
    print(f"\n📊 Total tweets in window: {total}")

    if not grouped:
        print("⚠️ No tweets found. Exiting.")
        return

    # ── AI filtering ──
    print("\n🤖 Running AI filter...\n")
    final_output = {}

    for acc, tweets in grouped.items():
        analyzed = []
        for tweet in tweets:
            result = analyze_tweet(tweet.rawContent)
            if not result or "SKIP" in result:
                continue

            # Media detection
            has_photo  = False
            photo_url  = None
            has_video  = False

            if tweet.media:
                if hasattr(tweet.media, "photos") and tweet.media.photos:
                    has_photo = True
                    photo_url = tweet.media.photos[0].url
                if hasattr(tweet.media, "videos") and tweet.media.videos:
                    has_video = True

            # Priority scoring
            priority = (
                3 if "PRIORITY: HIGH"   in result else
                2 if "PRIORITY: MEDIUM" in result else
                1
            )

            analyzed.append({
                "text":      result,
                "link":      f"https://x.com/{tweet.user.username}/status/{tweet.id}",
                "priority":  priority,
                "has_photo": has_photo,
                "photo_url": photo_url,
                "has_video": has_video,
            })

        if analyzed:
            analyzed.sort(key=lambda x: x["priority"], reverse=True)
            final_output[acc] = analyzed

    if not final_output:
        print("⚠️ No significant updates found after AI filtering.")
        return

    print(f"✅ {len(final_output)} accounts have significant updates")
    print("\n📨 Sending to Telegram...\n")

    # ── Send to Telegram ──
    async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:

        # Header
        await safe_send(bot,
            f"🌐 *GEOPOL BUDDY*\n"
            f"📅 {date_str}  |  ⏰ {time_str} IST\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 {len(final_output)} sources  |  🕐 Last 6 hours",
            parse_mode="Markdown"
        )
        await asyncio.sleep(2)

        # Per account
        for acc, items in final_output.items():

            # Account label
            label = f"🐦 *@{acc}*  —  {len(items)} update{'s' if len(items) > 1 else ''}"
            await safe_send(bot, label, parse_mode="Markdown")
            await asyncio.sleep(1)

            # Top tweet
            await send_tweet(bot, items[0], label="🔥 *TOP UPDATE*")
            await asyncio.sleep(1)

            # Other tweets
            for i, item in enumerate(items[1:], 1):
                await send_tweet(bot, item, label=f"📌 *Update {i}*")
                await asyncio.sleep(1)

        # Footer
        await safe_send(bot,
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 *Geopol Buddy*\n"
            f"_Sourced from monitored X intel accounts_\n"
            f"⏰ _Next update in 6 hours_",
            parse_mode="Markdown"
        )

    print("\n✅ Geopol Buddy — All done!")

if __name__ == "__main__":
    asyncio.run(main())
