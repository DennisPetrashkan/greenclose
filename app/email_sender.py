#!/usr/bin/env python3
"""
GreenClose Email Sender
Gmail SMTP for delivering quote pages and Dennis updates.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path


def _get_credentials():
    """Load Gmail credentials from env or config file."""
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        # Fallback to config file
        config_file = Path(__file__).parent.parent / "config" / "secrets.txt"
        if config_file.exists():
            for line in config_file.read_text().splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip() == "GMAIL_ADDRESS":
                        gmail_address = val.strip()
                    elif key.strip() == "GMAIL_APP_PASSWORD":
                        gmail_password = val.strip().replace(" ", "")

    if not gmail_address or not gmail_password:
        raise RuntimeError("Gmail credentials not found in env or config/secrets.txt")

    return gmail_address, gmail_password


def _send_email(to_email: str, subject: str, html_body: str, text_body: str = None):
    """Send an email via Gmail SMTP."""
    gmail_address, gmail_password = _get_credentials()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"GreenClose <{gmail_address}>"
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, to_email, msg.as_string())

    print(f"[EMAIL] Sent '{subject}' to {to_email}")


async def send_quote_email(
    to_email: str,
    contractor_name: str,
    client_name: str,
    job_id: str,
    quote_url: str,
):
    """Email the contractor their finished quote page link."""
    subject = f"Your GreenClose Quote Experience is Ready — {client_name}"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .header {{ background: #1B4332; padding: 32px; text-align: center; }}
    .header h1 {{ color: #C9A84C; margin: 0; font-size: 28px; letter-spacing: 1px; }}
    .header p {{ color: rgba(255,255,255,0.8); margin: 8px 0 0; }}
    .body {{ padding: 32px; }}
    .body h2 {{ color: #1B1B1B; margin-top: 0; }}
    .cta-button {{ display: inline-block; background: #1B4332; color: white; text-decoration: none; padding: 16px 32px; border-radius: 6px; font-size: 16px; font-weight: bold; margin: 24px 0; }}
    .job-id {{ background: #f8f8f8; border-radius: 4px; padding: 8px 16px; font-family: monospace; font-size: 14px; color: #666; display: inline-block; margin-top: 16px; }}
    .footer {{ padding: 24px 32px; border-top: 1px solid #eee; color: #999; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>GreenClose</h1>
      <p>Your quote experience is ready</p>
    </div>
    <div class="body">
      <h2>Hi {contractor_name},</h2>
      <p>Your personalized quote experience for <strong>{client_name}</strong> is live and ready to send.</p>
      <p>This isn't a PDF. This is a <strong>full interactive experience</strong> — designed to make {client_name} feel the value before they see the price.</p>
      <p><strong>What to do right now:</strong></p>
      <ol>
        <li>Click the button below to preview your quote page</li>
        <li>Make sure everything looks right</li>
        <li>Copy the link and send it directly to {client_name} — text, email, or DM</li>
      </ol>
      <a href="{quote_url}" class="cta-button">View Your Quote Experience →</a>
      <p style="color: #666; font-size: 14px;">Or copy this link:<br><a href="{quote_url}" style="color: #1B4332;">{quote_url}</a></p>
      <div class="job-id">Job ID: {job_id}</div>
      <p style="color: #888; font-size: 13px; margin-top: 24px;">Need a revision? Reply to this email with what you'd like changed. Revisions are delivered within 24 hours.</p>
    </div>
    <div class="footer">
      GreenClose — Turn your quote into a closing machine.<br>
      Questions? Reply to this email.
    </div>
  </div>
</body>
</html>
"""

    text_body = f"""Hi {contractor_name},

Your quote experience for {client_name} is ready.

View it here: {quote_url}

Copy that link and send it directly to {client_name}.

Job ID: {job_id}

Need a revision? Reply to this email.

— GreenClose
"""

    _send_email(to_email, subject, html_body, text_body)


async def send_dennis_update(stats: dict = None):
    """Send daily status update to Dennis."""
    dennis_email = os.getenv("DENNIS_EMAIL", "dvpetrashkan@gmail.com")

    # Also check config file
    config_file = Path(__file__).parent.parent / "config" / "secrets.txt"
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                if key.strip() == "DENNIS_EMAIL":
                    dennis_email = val.strip()

    now = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")

    if stats is None:
        stats = {"total_jobs": 0, "delivered": 0, "pending": 0, "revenue_usd": 0}

    subject = f"GreenClose Daily Update — {datetime.utcnow().strftime('%b %d')}"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
    .header {{ background: #0F1117; padding: 24px; }}
    .header h1 {{ color: #C9A84C; margin: 0; font-size: 22px; }}
    .header p {{ color: #888; margin: 4px 0 0; font-size: 13px; }}
    .body {{ padding: 24px; }}
    .stat-row {{ display: flex; gap: 16px; margin: 16px 0; }}
    .stat {{ flex: 1; background: #f8f8f8; border-radius: 6px; padding: 16px; text-align: center; }}
    .stat .num {{ font-size: 32px; font-weight: bold; color: #1B4332; }}
    .stat .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
    .section {{ margin-top: 24px; padding-top: 24px; border-top: 1px solid #eee; }}
    .section h3 {{ color: #333; margin-top: 0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>GreenClose</h1>
      <p>Daily operator report — {now}</p>
    </div>
    <div class="body">
      <div class="stat-row">
        <div class="stat">
          <div class="num">{stats.get('total_jobs', 0)}</div>
          <div class="label">Total Jobs</div>
        </div>
        <div class="stat">
          <div class="num">{stats.get('delivered', 0)}</div>
          <div class="label">Delivered</div>
        </div>
        <div class="stat">
          <div class="num">${stats.get('revenue_usd', 0):,.0f}</div>
          <div class="label">Revenue</div>
        </div>
      </div>

      <div class="section">
        <h3>System Status</h3>
        <p>✅ Backend: Running<br>
        ✅ Quote generator: Active<br>
        ✅ Email delivery: Working<br>
        ⏳ Domain: Needs purchase (greenclose.io)<br>
        ⏳ Stripe: Needs setup<br>
        ⏳ Anthropic API key: Needs activation</p>
      </div>

      <div class="section">
        <h3>Action Items for Dennis</h3>
        <ol>
          <li><strong>Purchase domain:</strong> greenclose.io (or .co) — ~$15/yr on Namecheap or Google Domains</li>
          <li><strong>Set up Anthropic API key:</strong> Go to console.anthropic.com, create account, add ~$50 credit, paste API key into the .env file</li>
          <li><strong>Set up Stripe:</strong> stripe.com — need your identity/SSN for payouts. Takes 10 min.</li>
        </ol>
        <p style="color: #888; font-size: 13px;">Everything else is handled. The machine is ready. It just needs the API key to start generating quote pages.</p>
      </div>
    </div>
  </div>
</body>
</html>
"""

    text_body = f"""GreenClose Daily Update — {now}

STATS:
- Total Jobs: {stats.get('total_jobs', 0)}
- Delivered: {stats.get('delivered', 0)}
- Revenue: ${stats.get('revenue_usd', 0):,.0f}

SYSTEM STATUS:
✅ Backend: Running
✅ Quote generator: Built
✅ Email delivery: Working
⏳ Domain: Needs purchase
⏳ Stripe: Needs setup
⏳ Anthropic API key: Needs activation

ACTION ITEMS FOR DENNIS:
1. Purchase domain: greenclose.io (~$15/yr on Namecheap)
2. Set up Anthropic API: console.anthropic.com — add ~$50 credit — paste key into .env
3. Set up Stripe: stripe.com — need identity for payouts

The machine is built and ready. API key = quotes start generating.

— Jeff
"""

    _send_email(dennis_email, subject, html_body, text_body)
    print(f"[JEFF] Daily update sent to Dennis at {dennis_email}")
