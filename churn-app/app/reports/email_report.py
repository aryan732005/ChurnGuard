"""Send executive summary PDF reports via SMTP."""

from __future__ import annotations

import json
import smtplib
import ssl
from datetime import datetime, timezone
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import (
    DATA_DIR,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)


def _queue_report(to_email: str, pdf_bytes: bytes, reason: str) -> dict:
    """Persist report for manual delivery when SMTP is not configured."""
    queue_dir = DATA_DIR / "pending_report_emails"
    queue_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_email = to_email.replace("@", "_at_").replace(".", "_")
    pdf_path = queue_dir / f"{stamp}_{safe_email}.pdf"
    meta_path = queue_dir / f"{stamp}_{safe_email}.json"
    pdf_path.write_bytes(pdf_bytes)
    meta_path.write_text(
        json.dumps(
            {
                "to": to_email,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "pdf_file": pdf_path.name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "sent": False,
        "queued": True,
        "message": (
            "SMTP is not configured — report saved for delivery. "
            "Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env.local, "
            f"or retrieve the PDF from data/pending_report_emails/{pdf_path.name}"
        ),
        "download_url": "/api/executive-summary.pdf",
    }


def send_executive_report(to_email: str, pdf_bytes: bytes) -> dict:
    """Email the executive summary PDF. Falls back to on-disk queue if SMTP unavailable."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return _queue_report(
            to_email,
            pdf_bytes,
            reason="SMTP not configured (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD)",
        )

    msg = MIMEMultipart()
    msg["Subject"] = "ChurnGuard Executive Summary Report"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(
        MIMEText(
            "Attached is your ChurnGuard executive summary report with model performance "
            "and business impact highlights.\n\n— ChurnGuard",
            "plain",
        )
    )

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename="churnguard-executive-summary.pdf",
    )
    msg.attach(attachment)

    try:
        if SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [to_email], msg.as_string())
    except Exception as exc:
        return _queue_report(to_email, pdf_bytes, reason=f"SMTP send failed: {exc}")

    return {
        "ok": True,
        "sent": True,
        "queued": False,
        "message": f"Report sent to {to_email}.",
        "download_url": "/api/executive-summary.pdf",
    }
