import os
import time
import random
import threading

import discord
from discord.ext import commands
import openai
from flask import Flask
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

openai.api_key = OPENAI_KEY



# === SETTINGS ===
REPLY_CHANCE = 3     # 1-in-3 chance to reply
CHANNEL_COOLDOWN = 25 # seconds between replies per channel
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

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

channel_last_reply = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} 🐌")

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    now = time.time()
    last = channel_last_reply.get(message.channel.id, 0)
    if now - last < CHANNEL_COOLDOWN:
        return

    if random.randint(1, REPLY_CHANCE) != 1:
        return

    user_text = message.content.strip()
    if not user_text:
        return

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

            channel_last_reply[message.channel.id] = now

    except Exception as e:
        print("Error:", e)

    await bot.process_commands(message)


# --- Flask web server so Render's Web Service sees an open port ---

app = Flask(__name__)

@app.route("/")
def home():
    return "Twirl is wandering Emerald Shores 🐌✨"

def run_web():
    # Render provides the port in the PORT env var
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start tiny web server in a background thread
    threading.Thread(target=run_web, daemon=True).start()

    # Start the Discord bot (Twirl)
    bot.run(DISCORD_TOKEN)

