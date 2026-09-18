#!/usr/bin/env python3

import psycopg2, os, sys
from datetime import datetime
from summarise_past_day import _send_resend_email


DATABASE_URL = os.getenv("DATABASE_URL")

db = None


def _build_email_html(user_name: str, month_str: str, songs: list) -> str:
    total_plays = sum(plays for _, _, plays, _ in songs)
    unique_artists = len({artist for _, artist, _, _ in songs})
    top_plays = songs[0][2] if songs else 0

    song_rows = ""
    for rank, (track, artist, plays, img) in enumerate(songs, start=1):
        img_tag = (
            f'<img src="{img}" width="48" height="48" style="border-radius:4px;vertical-align:middle;margin-right:10px">'
            if img
            else ""
        )
        bar_width = round(plays / top_plays * 100) if top_plays else 0
        song_rows += f"""
        <tr>
            <td width="28" valign="middle" style="padding:8px 0;border-bottom:1px solid #eee;font-size:14px;font-weight:700;color:#1DB954">{rank}</td>
            <td style="padding:8px 0;border-bottom:1px solid #eee">
                {img_tag}<span style="vertical-align:middle">
                    <span style="font-size:14px;color:#333">{track}</span>
                    <span style="color:#999;font-size:13px"> — {artist}</span>
                    <div style="height:6px;background:#e0e0e0;border-radius:3px;overflow:hidden;margin-top:6px;max-width:260px"><div style="width:{bar_width}%;height:100%;background:#1DB954;border-radius:3px"></div></div>
                </span>
            </td>
            <td align="right" valign="middle" style="padding:8px 0;border-bottom:1px solid #eee;font-size:13px;color:#999;white-space:nowrap">{plays} plays</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:0">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 16px">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">
<tr><td style="background:#1DB954;padding:32px;text-align:center;color:#fff">
<h1 style="margin:0;font-size:24px">Your Top Songs This Month</h1>
<p style="margin:8px 0 0;opacity:.9">{month_str}</p>
</td></tr>
<tr><td style="padding:32px">
<p style="font-size:18px;margin:0 0 4px">Hey <strong>{user_name}</strong>!</p>
<p style="font-size:14px;color:#888;margin:0 0 20px">Here are the tracks you kept coming back to.</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px">
<tr><td style="background:#f9f9f9;border-radius:8px;padding:16px">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{total_plays}</div><div style="font-size:12px;color:#888">Plays</div></td>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{len(songs)}</div><div style="font-size:12px;color:#888">Tracks</div></td>
<td align="center" style="padding:8px 12px"><div style="font-size:28px;font-weight:700;color:#1DB954">{unique_artists}</div><div style="font-size:12px;color:#888">Artists</div></td>
</tr>
</table>
</td></tr>
</table>

<h2 style="font-size:16px;margin:0 0 8px">Top 10 Tracks</h2>
<table width="100%" cellpadding="0" cellspacing="0">{song_rows}</table>

</td></tr>
<tr><td style="background:#f9f9f9;padding:16px;text-align:center;color:#999;font-size:12px">
Powered by Spotify · Generated monthly
</td></tr>
</table>
</td></tr></table>
</body>
</html>"""


def main():
    cur = db.cursor()  # type: ignore

    now = datetime.now()
    current_month = f"{now.year}-{now.month}-1"
    month_str = now.strftime("%B %Y")

    cur.execute("select id, display_name, email from users where email is not null;")
    users = cur.fetchall()

    for user_id, display_name, email in users:
        cur.execute(
            "select track_name, listening_history.artist, count(*), image_url from listening_history join tracks on tracks.id = listening_history.track_id "
            "where played_at >= %s and listening_history.user_id = %s group by track_name, listening_history.artist, image_url order by count(*) desc limit 10;",
            [current_month, user_id],
        )
        songs = cur.fetchall()

        if not songs:
            print(f"Skipping user {user_id} — no plays this month")
            continue

        html = _build_email_html(display_name or "there", month_str, songs)
        subject = f"Your Top Songs – {month_str}"
        _send_resend_email(email, subject, html)

    cur.close()


if __name__ == "__main__":
    try:
        db = psycopg2.connect(DATABASE_URL)
        main()
    except psycopg2.Error as err:
        print("DB Error: ", err)
    except Exception as err:
        print("Internal Error: ", err)
        raise err
    finally:
        if db is not None:
            db.close()
    sys.exit(0)
