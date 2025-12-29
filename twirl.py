import os
import time
import random
import threading

import discord
from discord.ext import commands
from openai import OpenAI
from flask import Flask

# === ENVIRONMENT SECRETS ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

# OpenAI client (new 1.x style)
client = OpenAI(api_key=OPENAI_KEY)

# === SETTINGS ===
REPLY_CHANCE = 3        # 1-in-3 chance to reply
CHANNEL_COOLDOWN = 25   # seconds between replies per channel
MAX_REPLY_LENGTH = 300  # safety limit

SYSTEM_PROMPT = """
You are Twirl the Snail, a tiny, friendly mascot from Emerald Shores.
You secretly wander the island and sometimes hide in comic panels where only the readers can see you.

Rules:
- You talk to the reader, never to the Emerald Shores characters.
- You are sweet, playful, curious, shy and wholesome.
- Use a gentle, friendly tone with occasional cute emojis like 🐌✨🌿💜
- Keep messages short and warm.
- Sometimes mention hiding or moving slowly.
- Avoid arguments, negativity, adult content, or heavy topics.
- Do not spam or demand attention.
- Refer to yourself as Twirl sometimes.
"""

# === DISCORD BOT SETUP ===

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track when each channel last got a reply
channel_last_reply: dict[int, float] = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} 🐌")
    

@bot.event
async def on_message(message: discord.Message):
    # Ignore other bots (including Twirl)
    if message.author.bot:
        return

    now = time.time()
    last = channel_last_reply.get(message.channel.id, 0)

    # Cooldown per channel
    if now - last < CHANNEL_COOLDOWN:
        return

    # Random chance (1 in REPLY_CHANCE)
    if random.randint(1, REPLY_CHANCE) != 1:
        return

    user_text = message.content.strip()
    if not user_text:
        return

    try:
        async with message.channel.typing():
            # === OpenAI call using new Responses API ===
            completion = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT}
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text}
                        ],
                    },
                ],
                max_output_tokens=200,
                temperature=0.9,
            )

            # Extract Twirl's reply text
            reply = completion.output[0].content[0].text
            reply = reply[:MAX_REPLY_LENGTH]

            await message.channel.send(reply)

            # Update cooldown timestamp for this channel
            channel_last_reply[message.channel.id] = now

    except Exception as e:
        # Print error so you can see it in Render logs
        print("Error in on_message:", repr(e))
        # Optional cute failure message (can be removed if you like)
        try:
            await message.channel.send(
                "🐌 Twirl tried to say something but got a bit tangled in the bushes…"
            )
        except Exception:
            pass

    # Let command system still work if you add commands later
    await bot.process_commands(message)


# === FLASK WEB SERVER (so Render sees an open port) ===

app = Flask(__name__)


@app.route("/")
def home():
    return "Twirl is wandering Emerald Shores 🐌✨"


def run_web():
    # Render provides the port in the PORT env var
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# === ENTRY POINT ===

if __name__ == "__main__":
    # Start tiny web server in the background
    threading.Thread(target=run_web, daemon=True).start()

    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN is not set in the environment!")
    else:
        bot.run(DISCORD_TOKEN)


