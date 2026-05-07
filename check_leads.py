#!/usr/bin/env python3
"""
GreenClose Lead Inbox Checker
Scans slothbound@gmail.com for:
1. Formspree intake submissions (contractor filled the form)
2. Direct replies from contractors who responded to outreach
3. Dennis replies / action updates

Run manually or from cron. Logs found leads to knowledge/leads.json.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from jeff_mail import read_inbox, send_email

LEADS_FILE = Path("knowledge/leads.json")
PROCESSED_FILE = Path("knowledge/processed_emails.json")


def load_json(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def extract_formspree_data(body: str) -> dict | None:
    """Extract contractor info from a Formspree email notification."""
    if "formspree" not in body.lower() and "form submission" not in body.lower():
        # Try to detect by content patterns
        if not any(k in body.lower() for k in ["contractor", "scope", "quote", "project"]):
            return None

    # Extract key-value pairs from Formspree format
    data = {}
    patterns = [
        (r'name[:\s]+(.+)', 'name'),
        (r'email[:\s]+([^\s]+@[^\s]+)', 'email'),
        (r'company[:\s]+(.+)', 'company'),
        (r'phone[:\s]+([\d\s\-\(\)]+)', 'phone'),
        (r'client[:\s]+(.+)', 'client_name'),
        (r'scope[:\s]+(.+)', 'scope'),
        (r'total[:\s]+\$?([\d,]+)', 'total'),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()

    return data if data else None


def is_contractor_reply(email_dict: dict) -> bool:
    """Detect if an email looks like a contractor reply to our outreach."""
    from_addr = email_dict.get("from", "").lower()
    subject = email_dict.get("subject", "").lower()
    body = email_dict.get("body", "").lower()

    # Skip obvious non-replies
    if any(skip in from_addr for skip in [
        "noreply", "no-reply", "mailer-daemon", "postmaster",
        "google", "formspree", "stripe", "adobe", "semrush", "vidiq", "playstation", "claude"
    ]):
        return False

    # Skip our own sent-to-self test
    if "slothbound@gmail.com" in from_addr:
        return False

    # Look for signals of a landscaper reply
    landscaping_signals = [
        "landscape", "lawn", "yard", "mow", "quote", "proposal", "customer",
        "client", "job", "project", "interested", "tell me more", "how does",
        "what is", "sounds good", "free quote", "demo"
    ]
    signal_count = sum(1 for s in landscaping_signals if s in body or s in subject)

    return signal_count >= 1


def is_dennis_reply(email_dict: dict) -> bool:
    """Detect if Dennis replied."""
    from_addr = email_dict.get("from", "").lower()
    return "dvpetrashkan" in from_addr or "dennis" in from_addr


def check_leads():
    """Main lead checking function."""
    print(f"[LEADS] Checking inbox at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load previously seen email IDs (we don't have IDs from jeff_mail, use subject+date combo)
    processed = set(load_json(PROCESSED_FILE)) if PROCESSED_FILE.exists() else set()
    leads = load_json(LEADS_FILE)

    # Read recent emails
    try:
        emails = read_inbox(unread_only=False, limit=20)
    except Exception as e:
        print(f"[LEADS] Error reading inbox: {e}")
        return

    new_leads = []
    dennis_replies = []

    for email_dict in emails:
        # Create a dedup key
        key = f"{email_dict.get('date','')}::{email_dict.get('subject','')}"
        if key in processed:
            continue

        processed.add(key)

        # Check for Dennis reply
        if is_dennis_reply(email_dict):
            dennis_replies.append(email_dict)
            print(f"[LEADS] ★ Dennis replied! Subject: {email_dict['subject']}")
            continue

        # Check for contractor lead
        if is_contractor_reply(email_dict):
            lead = {
                "type": "direct_reply",
                "from": email_dict.get("from"),
                "subject": email_dict.get("subject"),
                "date": email_dict.get("date"),
                "body_preview": email_dict.get("body", "")[:500],
                "status": "new",
                "logged_at": datetime.now().isoformat(),
            }
            leads.append(lead)
            new_leads.append(lead)
            print(f"[LEADS] ★★ CONTRACTOR LEAD: {email_dict.get('from')} — {email_dict.get('subject')}")

        # Check for Formspree submission
        formspree_data = extract_formspree_data(email_dict.get("body", ""))
        if formspree_data and "formspree" in email_dict.get("from", "").lower():
            lead = {
                "type": "intake_form",
                "from": email_dict.get("from"),
                "subject": email_dict.get("subject"),
                "date": email_dict.get("date"),
                "data": formspree_data,
                "status": "new",
                "logged_at": datetime.now().isoformat(),
            }
            leads.append(lead)
            new_leads.append(lead)
            print(f"[LEADS] ★★ INTAKE FORM SUBMISSION: {formspree_data.get('name', 'Unknown')}")

    # Save updated data
    save_json(LEADS_FILE, leads)
    save_json(PROCESSED_FILE, list(processed))

    # Alert Dennis if new leads found
    if new_leads:
        lead_summary = "\n".join([
            f"- {l['type'].upper()}: {l.get('from', '?')} — {l.get('subject', '?')}"
            for l in new_leads
        ])
        try:
            send_email(
                subject=f"GreenClose: {len(new_leads)} new lead(s) — action needed",
                body=f"""Dennis,

{len(new_leads)} new lead(s) just came in for GreenClose:

{lead_summary}

Check the inbox and reply to these contractors. Use this template:

---
Hey [Name] — thanks for reaching out. Happy to build a free demo for your next quote.

Just need a few details:
- Your client's name
- Scope of work (what you're doing for them)
- Your pricing/line items
- Your company name

Send those over and I'll have your interactive quote page ready within 24 hours. No catch — just want you to see the difference it makes.
---

All leads logged in knowledge/leads.json.

Jeff
"""
            )
            print(f"[LEADS] Alerted Dennis about {len(new_leads)} new lead(s)")
        except Exception as e:
            print(f"[LEADS] Could not alert Dennis: {e}")

    # Report Dennis replies
    if dennis_replies:
        print(f"[LEADS] Dennis replied {len(dennis_replies)} time(s):")
        for r in dennis_replies:
            print(f"  Subject: {r['subject']}")
            print(f"  Body: {r['body'][:300]}")
            print()

    if not new_leads and not dennis_replies:
        print("[LEADS] No new leads or Dennis replies. System is live and waiting.")

    return {
        "new_leads": len(new_leads),
        "dennis_replies": len(dennis_replies),
        "total_leads": len(leads),
    }


if __name__ == "__main__":
    result = check_leads()
    print(f"\n[LEADS] Summary: {result}")
