from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.idea_flow_webhook import SupabaseIdeaFlowService

router = APIRouter(tags=["telegram-miniapp"])


class MiniAppSubmitRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=2000)
    init_data: str = Field(min_length=1, max_length=12000)


def _validate_telegram_init_data(init_data: str) -> dict[str, Any]:
    """Validate Telegram Mini App initData using the bot token."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured.")

    pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    supplied_hash = pairs.pop("hash", "")
    if not supplied_hash:
        raise HTTPException(status_code=401, detail="Missing Telegram signature.")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, supplied_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature.")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth date.") from exc

    if auth_date <= 0 or abs(int(time.time()) - auth_date) > 86400:
        raise HTTPException(status_code=401, detail="Telegram session expired. Reopen the Mini App.")

    user: dict[str, Any] = {}
    raw_user = pairs.get("user")
    if raw_user:
        try:
            parsed = json.loads(raw_user)
            if isinstance(parsed, dict):
                user = parsed
        except json.JSONDecodeError:
            pass

    return {"user": user, "query_id": pairs.get("query_id", "")}


@router.get("/miniapp", response_class=HTMLResponse)
def telegram_miniapp() -> HTMLResponse:
    return HTMLResponse(MINIAPP_HTML)


@router.post("/miniapp/api/submit")
def submit_idea(request: MiniAppSubmitRequest) -> dict[str, Any]:
    telegram = _validate_telegram_init_data(request.init_data)
    user = telegram.get("user") or {}
    user_id = str(user.get("id") or "unknown")

    idea = request.idea.strip()
    if len(idea) < 3:
        raise HTTPException(status_code=422, detail="Idea is too short.")

    # The existing Idea Flow RPC expects a Telegram update id. A random positive
    # 63-bit integer keeps Mini App submissions isolated from real Bot API updates.
    synthetic_update_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    service = SupabaseIdeaFlowService()

    try:
        idea_id = service.capture(
            idea,
            actor=f"telegram-miniapp:{user_id}",
            update_id=synthetic_update_id,
        )
        result = service.score_content_job(idea_id)
        job = service.get_content_job(idea_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SoloForge pipeline failed: {str(exc)[:500]}") from exc

    return {
        "idea_id": idea_id,
        "score": result.get("score"),
        "decision": result.get("decision"),
        "reason": result.get("reason"),
        "status": job.get("status"),
        "hook": job.get("hook"),
        "caption": job.get("caption"),
    }


MINIAPP_HTML = r"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#101218">
  <title>SoloForge MiniBoss</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: var(--tg-theme-bg-color, #101218);
      --card: var(--tg-theme-secondary-bg-color, #191d26);
      --text: var(--tg-theme-text-color, #f5f7fb);
      --muted: var(--tg-theme-hint-color, #9aa4b2);
      --accent: var(--tg-theme-button-color, #38a7ff);
      --accent-text: var(--tg-theme-button-text-color, #ffffff);
      --border: rgba(255,255,255,.10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      width: min(720px, 100%);
      margin: 0 auto;
      padding: 18px 16px 32px;
    }
    .eyebrow {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: .08em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    h1 { margin: 0; font-size: clamp(28px, 8vw, 42px); line-height: 1.05; }
    .lead { margin: 10px 0 20px; color: var(--muted); line-height: 1.55; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 16px;
    }
    label { display: block; font-weight: 700; margin-bottom: 10px; }
    textarea {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: rgba(0,0,0,.14);
      color: var(--text);
      padding: 14px;
      font: inherit;
      font-size: 16px;
      outline: none;
    }
    textarea:focus { border-color: var(--accent); }
    .meta {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 12px;
      margin-top: 8px;
    }
    button {
      width: 100%;
      min-height: 52px;
      margin-top: 14px;
      border: 0;
      border-radius: 14px;
      background: var(--accent);
      color: var(--accent-text);
      font-size: 16px;
      font-weight: 800;
      cursor: pointer;
    }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .result {
      display: none;
      margin-top: 16px;
      padding: 16px;
      border-radius: 18px;
      background: var(--card);
      border: 1px solid var(--border);
    }
    .score-row {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
    }
    .score { font-size: 42px; font-weight: 900; }
    .badge {
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.08);
      font-size: 12px;
      font-weight: 800;
    }
    .reason { margin: 10px 0 0; color: var(--muted); line-height: 1.5; }
    .status {
      margin-top: 14px;
      font-size: 13px;
      color: var(--muted);
    }
    .error {
      display: none;
      margin-top: 12px;
      padding: 12px;
      border-radius: 12px;
      background: rgba(255,90,90,.12);
      color: #ffb5b5;
      line-height: 1.45;
    }
    .foot {
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">⚒️ SoloForge AI · MiniBoss</div>
    <h1>ส่งไอเดีย แล้วให้ MiniBoss คัดให้</h1>
    <p class="lead">พิมพ์ไอเดียคอนเทนต์หนึ่งเรื่อง ระบบจะส่งเข้า SoloForge pipeline และให้คะแนนเบื้องต้นทันที</p>

    <section class="card">
      <label for="idea">ไอเดียคอนเทนต์</label>
      <textarea id="idea" maxlength="2000" placeholder="เช่น ทำคลิปเปรียบเทียบ AI ฟรี 3 ตัวสำหรับสรุปประชุม..."></textarea>
      <div class="meta"><span>3–2,000 ตัวอักษร</span><span id="count">0/2000</span></div>
      <button id="submit" type="button">🧠 ให้ MiniBoss วิเคราะห์</button>
      <div class="error" id="error" role="alert"></div>
    </section>

    <section class="result" id="result" aria-live="polite">
      <div class="score-row">
        <div>
          <div style="font-size:12px;color:var(--muted)">MINIBOSS SCORE</div>
          <div class="score"><span id="score">—</span><span style="font-size:18px">/100</span></div>
        </div>
        <div class="badge" id="decision">—</div>
      </div>
      <p class="reason" id="reason"></p>
      <div class="status" id="job"></div>
    </section>

    <p class="foot" id="mode">กำลังเชื่อม Telegram…</p>
  </main>

  <script>
    (() => {
      const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
      const idea = document.getElementById('idea');
      const submit = document.getElementById('submit');
      const count = document.getElementById('count');
      const error = document.getElementById('error');
      const result = document.getElementById('result');
      const mode = document.getElementById('mode');

      if (tg) {
        tg.ready();
        tg.expand();
        mode.textContent = tg.initData ? 'เชื่อมกับ Telegram แล้ว' : 'โหมดพรีวิว — เปิดผ่าน @soloforge_inbox_bot เพื่อส่งงานจริง';
      } else {
        mode.textContent = 'โหมดพรีวิว — เปิดผ่าน Telegram เพื่อส่งงานจริง';
      }

      idea.addEventListener('input', () => {
        count.textContent = idea.value.length + '/2000';
      });

      submit.addEventListener('click', async () => {
        const text = idea.value.trim();
        error.style.display = 'none';
        result.style.display = 'none';

        if (text.length < 3) {
          error.textContent = 'พิมพ์ไอเดียอย่างน้อย 3 ตัวอักษร';
          error.style.display = 'block';
          return;
        }
        if (!tg || !tg.initData) {
          error.textContent = 'กรุณาเปิด Mini App ผ่าน Telegram @soloforge_inbox_bot';
          error.style.display = 'block';
          return;
        }

        submit.disabled = true;
        submit.textContent = 'กำลังวิเคราะห์…';

        try {
          const response = await fetch('/miniapp/api/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({idea: text, init_data: tg.initData})
          });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || 'ส่งงานไม่สำเร็จ');

          document.getElementById('score').textContent = payload.score ?? '—';
          document.getElementById('decision').textContent = payload.decision || payload.status || 'QUEUED';
          document.getElementById('reason').textContent = payload.reason || 'MiniBoss รับงานแล้ว';
          document.getElementById('job').textContent = 'SoloForge Job #' + payload.idea_id + ' · ' + (payload.status || 'NEW');
          result.style.display = 'block';

          if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } catch (err) {
          error.textContent = err && err.message ? err.message : 'เกิดข้อผิดพลาด';
          error.style.display = 'block';
          if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
        } finally {
          submit.disabled = false;
          submit.textContent = '🧠 ให้ MiniBoss วิเคราะห์';
        }
      });
    })();
  </script>
</body>
</html>"""
