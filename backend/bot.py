"""
Artemis Discord Bot — interactive alert Q&A.

When an alert fires, the notification layer creates a Discord thread and stores
its ID in the detections table. This bot listens for messages in those threads
and answers operator questions using the detection context + Azure OpenAI.

Run alongside the FastAPI server:
    python bot.py

Requires:
    DISCORD_BOT_TOKEN   — from Discord Developer Portal → Bot → Token
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
    DATABASE_URL

Bot permissions needed (when inviting to server):
    - Read Messages / View Channels
    - Send Messages
    - Send Messages in Threads
    - Read Message History
Enable "Message Content Intent" in Discord Developer Portal → Bot → Privileged Gateway Intents.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import discord
from dotenv import load_dotenv
from openai import AzureOpenAI

from db import SessionLocal, get_detection_context_for_thread

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# Thread pool for blocking DB + LLM calls (discord.py runs on asyncio)
_executor = ThreadPoolExecutor(max_workers=4)

CHAT_SYSTEM_PROMPT = """You are Artemis, an AI assistant for an offshore oil platform monitoring system.
An operator is asking a question about a specific detection alert.
Answer using only the detection data and AI analysis provided below — do not invent facts.
Be concise (2–4 sentences), factual, and operator-friendly.
If the answer is not in the context, say so clearly."""


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _build_context_block(ctx: dict) -> str:
    """Format the detection context dict into a prompt block."""
    lines = [
        f"DETECTION: {ctx['detection_type']} | {ctx['severity']}",
        f"Asset: {ctx['asset_name']} ({ctx['asset_tag']}) — {ctx['area']}",
        f"Detected: {ctx['detected_at']}",
        "",
    ]
    if ctx.get("what"):
        lines.append(f"AI SUMMARY: {ctx['what']}")
    if ctx.get("why"):
        lines.append(f"ROOT CAUSE: {ctx['why']}")
    if ctx.get("confidence"):
        lines.append(f"Confidence: {ctx['confidence']}")
    if ctx.get("remaining_life_years") is not None:
        lines.append(f"Estimated remaining life: {ctx['remaining_life_years']:.1f} years")
    if ctx.get("evidence"):
        lines.append("Evidence:")
        for e in ctx["evidence"]:
            lines.append(f"  • {e}")
    if ctx.get("recommended_actions"):
        lines.append("Recommended actions:")
        for a in ctx["recommended_actions"]:
            lines.append(f"  • {a}")
    if ctx.get("relevant_docs"):
        lines.append("Referenced documents:")
        for doc in ctx["relevant_docs"]:
            title = doc.get("title", "Unknown")
            doc_type = doc.get("doc_type", "")
            tree_path = doc.get("tree_path", "")
            snippet = doc.get("snippet", "")
            lines.append(f"  [{doc_type}] {title}")
            if tree_path:
                lines.append(f"    Section: {tree_path}")
            if snippet:
                lines.append(f"    Extract: {snippet[:300]}")
    if ctx.get("past_resolutions"):
        lines.append("Past resolutions (same asset, same detection type):")
        for r in ctx["past_resolutions"]:
            lines.append(
                f"  Detected: {r.get('detected_at', '?')} | "
                f"Severity: {r.get('severity', '?')} | "
                f"Resolved: {r.get('resolved_at', '?')} by {r.get('resolved_by', 'unknown')}"
            )
            if r.get("resolution_notes"):
                lines.append(f"  Resolution: {r['resolution_notes']}")
    return "\n".join(lines)


def _call_llm(context_block: str, question: str) -> str:
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": f"{context_block}\n\nOPERATOR QUESTION: {question}"},
        ],
        temperature=0.3,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def _fetch_and_answer(thread_id: str, question: str) -> str | None:
    """Blocking: fetch context from DB then call LLM. Returns answer or None if not an alert thread."""
    db = SessionLocal()
    try:
        ctx = get_detection_context_for_thread(db, thread_id)
    finally:
        db.close()

    if ctx is None:
        return None  # not an alert thread — bot stays silent

    context_block = _build_context_block(ctx)
    return _call_llm(context_block, question)


# ---------------------------------------------------------------------------
# Discord client
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    logger.info("Artemis bot connected as %s (ID: %s)", bot.user, bot.user.id)


@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from any bot (including self)
    if message.author.bot:
        return

    # Only respond inside threads
    if not isinstance(message.channel, discord.Thread):
        return

    thread_id = str(message.channel.id)

    # Run blocking DB + LLM work in the thread pool so we don't block the event loop
    loop = asyncio.get_event_loop()
    async with message.channel.typing():
        try:
            answer = await loop.run_in_executor(
                _executor, _fetch_and_answer, thread_id, message.content
            )
        except Exception as exc:
            logger.error("Error answering question in thread %s: %s", thread_id, exc)
            await message.reply("Sorry, I ran into an error processing your question. Please try again.")
            return

    if answer is None:
        return  # not an alert thread — stay silent

    await message.reply(answer)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in the environment.")
    bot.run(token, log_handler=None)  # logging already configured above
