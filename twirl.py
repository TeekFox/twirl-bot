import os
import time
import random
import threading

import discord
from discord.ext import commands
from flask import Flask

from openai import OpenAI


# === ENV VARS ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN env var is missing!")
if not OPENAI_KEY:
    print("ERROR: OPENAI_KEY env var is missing!")

client = OpenAI(api_key=OPENAI_KEY)


# === SETTINGS ===
REPLY_CHANCE = 3        # 1-in-3 chance to reply to normal messages
CHANNEL_COOLDOWN = 25   # seconds between replies per channel
MAX_REPLY_LENGTH = 300

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

# === DISCORD SETUP ===

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track last reply time per channel so we don’t spam
channel_last_reply: dict[int, float] = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} 🐌")
    print("Twirl is ready to wander Emerald Shores!")


@bot.event
async def on_message(message: discord.Message):
    # Ignore other bots (including Twirl herself)
    if message.author.bot:
        return

    content = message.content.strip()
    if not content:
        return

    content_lower = content.lower()

    # --- FORCE REPLY IF NAME IS MENTIONED ---
    name_mentioned = "twirl" in content_lower

    now = time.time()
    last = channel_last_reply.get(message.channel.id, 0)

    # Cooldown only applies if her name is NOT mentioned
    if not name_mentioned and (now - last < CHANNEL_COOLDOWN):
        return

    # Random chance only applies if her name is NOT mentioned
    if not name_mentioned and random.randint(1, REPLY_CHANCE) != 1:
        return

    try:
        async with message.channel.typing():
            # Call OpenAI for a reply
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=200,
                temperature=0.9,
            )

            reply = response.choices[0].message.content or ""
            reply = reply[:MAX_REPLY_LENGTH]

            if not reply.strip():
                # Just in case OpenAI returns something weird/empty
                reply = "🐌 Twirl got a little shy and lost her words for a moment… could you try asking again?"

            await message.channel.send(reply)

            # Only update cooldown when she actually sends a message
            channel_last_reply[message.channel.id] = now

    except Exception as e:
        # Log error in Render logs
        print("Error while generating or sending reply:", repr(e))
        # Cute fallback so she still responds
        try:
            await message.channel.send(
                "🐌 Oh no, my thoughts got tangled in the bushes… Teek, could you check my logs on Render?"
            )
        except Exception as send_err:
            print("Error sending fallback message:", repr(send_err))

    # Let commands (like !something) still work
    await bot.process_commands(message)


# === TINY FLASK WEB SERVER FOR RENDER ===

app = Flask(__name__)


@app.route("/")
def home():
    return "Twirl is wandering Emerald Shores 🐌✨"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# === ENTRY POINT ===

if __name__ == "__main__":
    # Start the little web server in the background (for Render)
    threading.Thread(target=run_web, daemon=True).start()

    # Start the Discord bot
    bot.run(DISCORD_TOKEN)

