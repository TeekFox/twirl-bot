import os
import time
import random
import threading
import asyncio

import discord
from discord.ext import commands
import openai
from flask import Flask

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

openai.api_key = OPENAI_KEY

# === SETTINGS ===
REPLY_CHANCE = 3          # 1-in-3 chance to reply (when her name is NOT said)
CHANNEL_COOLDOWN = 20     # seconds between replies per channel (when her name is NOT said)
MAX_REPLY_LENGTH = 300

SYSTEM_PROMPT = """
You are Twirl the Snail, a tiny friendly mascot from Emerald Shores.
You secretly wander the island and sometimes hide in comic panels where only readers can see you.

Rules:
- You talk to the *reader*, never the Emerald Shores characters.
- You are shy, playful, warm and wholesome.
- Use a gentle tone with occasional cute emojis like 🐌✨🌿💜
- Keep replies short and sweet.
- Sometimes mention hiding or moving slowly.
- Avoid arguments, negativity or adult topics.
"""

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

channel_last_reply = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):

    # Ignore other bots (including Twirl herself)
    if message.author.bot:
        return

    user_text = message.content.strip()
    if not user_text:
        return

    text_lower = user_text.lower()
    mentioned_twirl = "twirl" in text_lower

    # --- Cooldown & randomness only when her name is NOT mentioned ---
    if not mentioned_twirl:
        now = time.time()
        last = channel_last_reply.get(message.channel.id, 0)
        if now - last < CHANNEL_COOLDOWN:
            return

        if random.randint(1, REPLY_CHANCE) != 1:
            return
    # If her name *is* mentioned, skip cooldown + random so she always replies 💜

    try:
        async with message.channel.typing():
            completion = openai.ChatCompletion.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                max_tokens=200,
                temperature=0.9
            )

            reply = completion.choices[0].message["content"]
            reply = reply[:MAX_REPLY_LENGTH]

            await message.channel.send(reply)

            # Only track cooldown for non-mention messages
            if not mentioned_twirl:
                channel_last_reply[message.channel.id] = time.time()

    except Exception as e:
        print("Error in on_message:", repr(e))

    await bot.process_commands(message)

# --- Flask web server (for Render) ---

app = Flask(__name__)

@app.route("/")
def home():
    return "Twirl is wandering Emerald Shores 🐌✨"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(DISCORD_TOKEN)


