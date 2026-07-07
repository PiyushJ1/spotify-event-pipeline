import os
import sys
import json
import logging
from typing import Sequence
from collections import Counter
from datetime import datetime, timezone, timedelta

import requests
from sqlalchemy import select
from sqlalchemy.orm import joinedload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.common.db import SessionLocal
from src.common.models import ListeningHistory, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("summarise_past_day")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL", "Spotify Wrapped Daily <onboarding@resend.dev>"
)


def _build_user_payload(user: User, history: Sequence[ListeningHistory]) -> dict:
    unique_artists = set()
    artist_counter = Counter()
    track_counter = Counter()
    total_seconds = 0
    listening_history = []

    for play in history:
        duration_seconds = play.track.duration_ms / 1000
        total_seconds += duration_seconds

        artists = [a.strip() for a in str(play.artist).split(",")]
        for artist in artists:
            unique_artists.add(artist)
            artist_counter[artist] += 1

        track_counter[play.track_name] += 1

        listening_history.append(
            {
                "song_name": play.track_name,
                "artist": play.artist,
                "album": play.track.album,
                "image_url": play.track.image_url,
                "duration_in_seconds": duration_seconds,
                "played_at": play.played_at.isoformat(),
            }
        )

    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "user": {
            "id": user.id,
            "display_name": user.display_name,
        },
        "summary": {
            "total_tracks": len(history),
            "total_minutes": round(total_seconds / 60),
            "unique_artist_count": len(unique_artists),
            "top_artists": [
                {"artist": artist, "plays": plays}
                for artist, plays in artist_counter.most_common(5)
            ],
            "top_tracks": [
                {
                    "song": song,
                    "plays": plays,
                    "image_url": next(
                        (p.track.image_url for p in history if p.track_name == song),
                        None,
                    ),
                }
                for song, plays in track_counter.most_common(5)
            ],
        },
        "listening_history": listening_history,
    }


def _call_openrouter_insights(payload: dict) -> dict | None:
    system_prompt = """
        You are an expert Spotify music analyst.

        Given a user's listening history, analyze their day and return ONLY valid JSON with exactly these fields:

        {
        "headline": "...",
        "mood": "...",
        "energy_score": 0,
        "discovery_score": 0,
        "artist_loyalty": "...",
        "listening_personality": "...",
        "highlight": "...",
        "genre_vibe": "...",
        "repeat_obsession": "...",
        "time_pattern": "...",
        "recommendation": "...",
        "fun_fact": "..."
        }

        Rules:
        - Make observations specific to THIS listening history.
        - Avoid generic statements.
        - If there isn't enough evidence for something, say so rather than inventing facts.
        - Do not mention "the user". Instead say "You".
        - Do not mention that you're an AI.
        - Return ONLY valid JSON.
    """

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, indent=2)},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
                "max_tokens": 500,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        return json.loads(content)
    except Exception as e:
        logger.exception("OpenRouter request failed: %s", e)
        return None


def _build_email_html(
    user_name: str,
    summary: dict,
    insights: dict,
    top_tracks: list,
    top_artists: list,
) -> str:
    date_str = datetime.now(timezone.utc).date().isoformat()

    top_tracks_rows = ""
    for t in top_tracks[:5]:
        img = t.get("image_url") or ""
        img_tag = (
            f'<img src="{img}" width="48" height="48" style="border-radius:4px;vertical-align:middle;margin-right:10px">'
            if img
            else ""
        )
        top_tracks_rows += f"""
        <tr>
            <td style="padding:8px 0;border-bottom:1px solid #eee">
                {img_tag}<span style="vertical-align:middle">{t["song"]} <span style="color:#999">({t["plays"]} plays)</span></span>
            </td>
        </tr>"""

    top_artists_rows = ""
    for a in top_artists[:5]:
        top_artists_rows += f"""
        <tr>
            <td style="padding:6px 0;border-bottom:1px solid #f0f0f0">
                <span style="font-size:14px">{a["artist"]} <span style="color:#999">({a["plays"]} plays)</span></span>
            </td>
        </tr>"""

    headline = insights.get("headline", "")
    mood = insights.get("mood", "")
    energy = insights.get("energy_score")
    discovery = insights.get("discovery_score")
    artist_loyalty = insights.get("artist_loyalty", "")
    personality = insights.get("listening_personality", "")
    highlight = insights.get("highlight", "")
    genre_vibe = insights.get("genre_vibe", "")
    repeat = insights.get("repeat_obsession", "")
    time_pattern = insights.get("time_pattern", "")
    hidden_gem = insights.get("hidden_gem", "")
    recommendation = insights.get("recommendation", "")
    fun_fact = insights.get("fun_fact", "")

    scores_section = ""
    if energy is not None or discovery is not None:
        bar = (
            lambda v: f'<div style="height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden;margin:4px 0 12px"><div style="width:{max(0, min(100, v * 10))}%;height:100%;background:#1DB954;border-radius:4px"></div></div>'
        )
        scores_section = '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px"><tr>'
        if energy is not None:
            scores_section += f'<td width="50%" style="padding:0 8px 0 0"><div style="font-size:12px;color:#888">Energy</div><div style="font-size:22px;font-weight:700;color:#333">{energy}/10</div>{bar(energy)}</td>'
        if discovery is not None:
            scores_section += f'<td width="50%" style="padding:0 0 0 8px"><div style="font-size:12px;color:#888">Discovery</div><div style="font-size:22px;font-weight:700;color:#333">{discovery}/10</div>{bar(discovery)}</td>'
        scores_section += "</tr></table>"

    insight_cards = ""
    sections = [
        ("Artist Loyalty", artist_loyalty),
        ("Listening Personality", personality),
        ("Repeat Obsession", repeat),
        ("Peak Listening Time", time_pattern),
        ("Recommendation", recommendation),
    ]
    for label, value in sections:
        if value:
            safe = value.replace("<", "&lt;").replace(">", "&gt;")
            insight_cards += f'<tr><td style="padding:10px 0;border-bottom:1px solid #f0f0f0"><div style="font-size:12px;color:#888;margin-bottom:2px">{label}</div><div style="font-size:14px;color:#333">{safe}</div></td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:0">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 16px">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">
<tr><td style="background:#1DB954;padding:32px;text-align:center;color:#fff">
<h1 style="margin:0;font-size:24px">Your Spotify Daily Wrapped</h1>
<p style="margin:8px 0 0;opacity:.9">{date_str}</p>
</td></tr>
<tr><td style="padding:32px">
<p style="font-size:18px;margin:0 0 4px">Hey <strong>{user_name}</strong>!</p>
{headline and f'<p style="font-size:20px;font-weight:600;color:#1DB954;margin:0 0 20px">{headline}</p>' or '<p style="font-size:14px;color:#888;margin:0 0 20px">Here is your day in music.</p>'}

{mood and f'<p style="font-size:16px;font-style:italic;color:#555;margin:0 0 20px">🎵 {mood}</p>' or ''}

<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px">
<tr><td style="background:#f9f9f9;border-radius:8px;padding:16px">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{summary["total_tracks"]}</div><div style="font-size:12px;color:#888">Tracks</div></td>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{summary["total_minutes"]}</div><div style="font-size:12px;color:#888">Minutes</div></td>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{summary["unique_artist_count"]}</div><div style="font-size:12px;color:#888">Artists</div></td>
</tr>
</table>
</td></tr>
</table>

{scores_section}

<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px">
<tr><td valign="top" width="50%" style="padding-right:12px">
<h2 style="font-size:16px;margin:0 0 8px">Top Tracks</h2>
<table width="100%" cellpadding="0" cellspacing="0">{top_tracks_rows}</table>
</td>
<td valign="top" width="50%" style="padding-left:12px">
<h2 style="font-size:16px;margin:0 0 8px">Top Artists</h2>
<table width="100%" cellpadding="0" cellspacing="0">{top_artists_rows}</table>
</td></tr>
</table>

{genre_vibe and f'<p style="font-size:14px;color:#555;margin:0 0 8px"><strong>Vibe:</strong> {genre_vibe}</p>' or ''}
{highlight and f'<p style="font-size:14px;color:#555;margin:0 0 8px"><strong>Highlight:</strong> {highlight}</p>' or ''}
{fun_fact and f'<p style="font-size:14px;color:#555;margin:0 0 8px"><strong>Fun fact:</strong> {fun_fact}</p>' or ''}

{insight_cards and f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px">{insight_cards}</table>' or ''}

</td></tr>
<tr><td style="background:#f9f9f9;padding:16px;text-align:center;color:#999;font-size:12px">
Powered by Spotify · Generated daily at midnight
</td></tr>
</table>
</td></tr></table>
</body>
</html>"""


def _send_resend_email(to_email: str, subject: str, html_body: str):
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Email sent to %s — id: %s", to_email, resp.json().get("id"))
    except Exception as e:
        logger.exception("Resend email failed for %s: %s", to_email, e)


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    db = SessionLocal()

    try:
        users: list[User] = db.query(User).all()
    finally:
        db.close()

    for user in users:
        if not user.email:
            logger.info("Skipping user %s — no email on record", user.id)
            continue

        db = SessionLocal()
        try:
            history = db.scalars(
                select(ListeningHistory)
                .options(joinedload(ListeningHistory.track))
                .where(
                    ListeningHistory.user_id == user.id,
                    ListeningHistory.played_at >= cutoff,
                )
                .order_by(ListeningHistory.played_at.desc())
            ).all()
        finally:
            db.close()

        if not history:
            logger.info("Skipping user %s — no listening history in last 24h", user.id)
            continue

        payload = _build_user_payload(user, history)
        logger.info(
            "User %s: %d tracks, getting insights...",
            user.id,
            payload["summary"]["total_tracks"],
        )

        insights = _call_openrouter_insights(payload)
        if not insights:
            logger.warning("No insights for user %s, sending stats-only email", user.id)

        html = _build_email_html(
            user_name=user.display_name or "there",
            summary=payload["summary"],
            insights=insights or {},
            top_tracks=payload["summary"]["top_tracks"],
            top_artists=payload["summary"]["top_artists"],
        )

        subject = f"Your Spotify Daily Wrap – {payload['date']}"
        _send_resend_email(user.email, subject, html)


if __name__ == "__main__":
    main()
