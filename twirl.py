import os
import time
import random
import threading

import discord
from discord.ext import commands
from flask import Flask

from openai import OpenAI


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)


REPLY_CHANCE = 3
CHANNEL_COOLDOWN = 25
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
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    content = message.content.strip()
    if not content:
        return

    name_mentioned = "twirl" in content.lower()

    now = time.time()
    last = channel_last_reply.get(message.channel.id, 0)

    if not name_mentioned and (now - last < CHANNEL_COOLDOWN):
        return

    if not name_mentioned and random.randint(1, REPLY_CHANCE) != 1:
        return

    try:
        async with message.channel.typing():

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                max_tokens=200,
                temperature=0.9,
            )

            reply = response.choices[0].message.content
            reply = reply[:MAX_REPLY_LENGTH]

            await message.channel.send(reply)

            channel_last_reply[message.channel.id] = now

    except Exception as e:
        print("OPENAI ERROR:", e)

        try:
            await message.channel.send(
                "🐌 Oh no, my thoughts got tangled in the bushes… Teek, could you check my logs on Render?"
            )
        except:
            pass

    await bot.process_commands(message)


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


