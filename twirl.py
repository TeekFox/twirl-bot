import os
import time
import random
import threading

import discord
from discord.ext import commands
import openai
from flask import Flask

# === ENV VARS ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

openai.api_key = OPENAI_KEY

# === SETTINGS ===
REPLY_CHANCE = 3         # 1-in-3 random chance (for normal messages)
CHANNEL_COOLDOWN = 25    # seconds between random replies per channel
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

# Per-channel cooldown tracking
channel_last_reply = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} 🐌")
    print(f"DISCORD_TOKEN length: {len(DISCORD_TOKEN) if DISCORD_TOKEN else 'None'}")


@bot.event
async def on_message(message: discord.Message):
    # Don't respond to other bots (including Twirl herself)
    if message.author.bot:
        return

    content = message.content.strip()
    if not content:
        return

    lower = content.lower()

    # --- Detect if Twirl is directly addressed ---
    mentioned_by_name = "twirl" in lower
    mentioned_by_mention = False
    if bot.user:
        mentioned_by_mention = bot.user in message.mentions

    must_reply = mentioned_by_name or mentioned_by_mention

    now = time.time()
    last = channel_last_reply.get(message.channel.id, 0)

    # --- Random / cooldown logic (ignored if must_reply is True) ---
    if not must_reply:
        # Respect cooldown for random replies
        if now - last < CHANNEL_COOLDOWN:
            return

        # 1-in-REPLY_CHANCE chance to reply
        if random.randint(1, REPLY_CHANCE) != 1:
            return

    # If we reach here, Twirl has decided to reply
    try:
        print(f"[Twirl] Generating reply. Must_reply={must_reply}, content='{content}'")

        async with message.channel.typing():
            completion = openai.ChatCompletion.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=200,
                temperature=0.9,
            )

        reply = completion.choices[0].message["content"]
        reply = reply[:MAX_REPLY_LENGTH]

        await message.channel.send(reply)

        # Update cooldown *after* a successful send (for random replies)
        channel_last_reply[message.channel.id] = now

    except Exception as e:
        # Print full error to Render logs
        print("Error while generating or sending reply:", repr(e))

        # Try to send a small error hint into Discord (optional but helpful)
        try:
            await message.channel.send(
                "🐌 Oh no, my thoughts got tangled in the bushes… "
                "Teek, could you check my logs on Render?"
            )
        except Exception as send_err:
            print("Also failed to send error message:", repr(send_err))

    # Let commands still work if you add any later
    await bot.process_commands(message)


# === Tiny Flask server so Render sees an open port ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Twirl is wandering Emerald Shores 🐌✨"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    # Start the tiny web server in the background
    threading.Thread(target=run_web, daemon=True).start()

    print("Starting Twirl…")
    print(f"Token starts with: {DISCORD_TOKEN[:5] if DISCORD_TOKEN else 'None'}")
    bot.run(DISCORD_TOKEN)


