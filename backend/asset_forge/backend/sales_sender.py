"""Outbound email sender for SoloForge Sales Inbox.

Uses Gmail SMTP with a Google App Password. Sending is disabled unless all
required SALES_GMAIL_* environment variables are configured.
"""

from __future__ import annotations

import email.utils
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

try:\n    from backend.idea_flow_webhook import _supabase_request\nexcept ImportError:\n    from backend.asset_forge.backend.idea_flow_webhook import _supabase_request


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _recipient_from_channel(channel: str) -> str:
    value = (channel or "").strip()
    if "@" not in value or " " in value:
        raise ValueError("Lead contact_channel must contain a valid email address before sending")
    return value


def send_sales_email(lead: dict[str, Any]) -> dict[str, str]:
    sender = _required("SALES_GMAIL_EMAIL")
    app_password = _required("SALES_GMAIL_APP_PASSWORD").replace(" ", "")
    recipient = _recipient_from_channel(str(lead.get("contact_channel") or ""))
    subject = str(lead.get("outreach_subject") or "").strip()
    body = str(lead.get("outreach_body") or "").strip()
    if not subject or not body:
        raise ValueError("Outreach draft is missing")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = email.utils.make_msgid(domain=sender.split("@", 1)[-1])
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(message)

    message_id = str(message["Message-ID"])
    lead_id = int(lead["id"])
    rows = _supabase_request(
        "PATCH",
        f"sales_leads?id=eq.{lead_id}",
        body={
            "status": "CONTACTED",
            "sender_email": sender,
            "message_id": message_id,
            "last_error": None,
        },
        prefer="return=representation",
    ) or []
    if not rows:
        raise RuntimeError("Email sent but lead status update failed")
    return {"recipient": recipient, "sender": sender, "message_id": message_id}
