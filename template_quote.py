#!/usr/bin/env python3
"""
GreenClose Template Quote Generator
Produces a quality HTML quote experience WITHOUT requiring the Claude API.
Uses smart templates with Hormozi-style sales psychology baked in.

Usage:
  python3 template_quote.py --job_id JOB001 --out frontend/quotes/JOB001.html

Or import and use generate_from_dict(job_data) directly.
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# EMOTIONAL ANGLES BY SCOPE KEYWORD
# ─────────────────────────────────────────────────────────────

SCOPE_ANGLES = {
    "sod": ("A lawn that looks like it's always been there", "lush, full lawn that your neighbors will notice"),
    "patio": ("Your backyard becomes a place you actually use", "outdoor living space that adds real value to your home"),
    "paver": ("Outdoor living space built to last decades", "premium hardscape that transforms how you use your property"),
    "retaining wall": ("Stop losing your yard to erosion — permanently", "structural solution that reclaims usable yard space"),
    "irrigation": ("Never drag a hose again. Your lawn waters itself.", "automated system that saves hours every week"),
    "lighting": ("Your home looks different at night. In the best way.", "landscape lighting that makes your property stand out after dark"),
    "drainage": ("No more standing water. No more mosquitoes.", "proper drainage that protects your foundation and landscaping investment"),
    "mulch": ("Fresh beds change everything — fastest ROI in landscaping", "crisp, clean beds that transform your property's first impression"),
    "fence": ("Privacy, security, and a defined outdoor space", "fencing that gives you the backyard privacy you've been wanting"),
    "tree": ("Privacy, shade, and curb appeal that grows over time", "mature plantings that add permanent value and beauty"),
    "shrub": ("Structure, privacy, and year-round visual interest", "plantings that define your space and create a finished look"),
    "firepit": ("The backyard your neighbors wish they had", "outdoor gathering space built for family and entertaining"),
    "kitchen": ("Outdoor kitchen that pays for itself in one summer", "fully equipped outdoor cooking and entertaining space"),
    "pergola": ("Shade, structure, and outdoor living — all in one", "covered outdoor space you can use year-round"),
    "cleanup": ("A fresh start for your property", "thorough cleanup that gets your landscaping back to its best"),
    "spring": ("Start the season with a property you're proud of", "seasonal refresh that sets up your landscaping for success"),
    "lawn": ("A lawn that makes you want to spend time outside", "healthy, thick lawn that boosts your property's curb appeal"),
    "design": ("Your vision, expertly executed", "custom landscape design tailored specifically to your property and lifestyle"),
}


def detect_dream_outcome(scope_text: str) -> tuple[str, str]:
    """Detect the primary emotional angle from scope text."""
    scope_lower = scope_text.lower()
    for keyword, (headline, subtext) in SCOPE_ANGLES.items():
        if keyword in scope_lower:
            return headline, subtext
    return "A property transformation you'll be proud of", "complete landscaping service tailored to your specific project"


def format_currency(amount) -> str:
    try:
        return f"${float(str(amount).replace(',', '').replace('$', '')):,.0f}"
    except (ValueError, TypeError):
        return str(amount)


def parse_pricing_lines(pricing_text: str) -> list[dict]:
    """Parse pricing breakdown into structured line items."""
    lines = []
    for line in pricing_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Try to detect amount: look for $ or a number at end
        match = re.search(r'\$?([\d,]+(?:\.\d{2})?)\s*$', line)
        if match:
            amount = match.group(1).replace(',', '')
            label = line[:match.start()].strip().rstrip(':-–—').strip()
            lines.append({"label": label, "amount": float(amount)})
        else:
            lines.append({"label": line, "amount": None})
    return lines


def split_scope_phases(scope_text: str) -> list[str]:
    """Split scope into phases/bullets for story presentation."""
    phases = []
    for line in scope_text.strip().splitlines():
        line = line.strip().lstrip('•-–—*').strip()
        if line:
            phases.append(line)
    return phases


def generate_scope_story(phases: list[str]) -> str:
    """Convert raw scope bullets into story HTML."""
    connectors = [
        "We start by", "Next comes", "Then we", "From there,",
        "Building on that,", "To finish,", "Finally,"
    ]
    items_html = []
    for i, phase in enumerate(phases):
        connector = connectors[i] if i < len(connectors) else "We also"
        # If the phase already starts with a verb phrase, don't double-prefix
        phase_lower = phase.lower()
        if any(phase_lower.startswith(v) for v in ["install", "build", "create", "remove", "grade", "add", "plant"]):
            story_text = phase[0].upper() + phase[1:]
        else:
            story_text = f"{connector} {phase[0].lower()}{phase[1:]}"
        items_html.append(f"""
            <div class="scope-item">
                <div class="scope-num">{str(i+1).zfill(2)}</div>
                <div class="scope-text">{story_text}</div>
            </div>""")
    return "\n".join(items_html)


def generate_pricing_rows(pricing_lines: list[dict], total: float) -> str:
    """Generate pricing table rows HTML."""
    rows = []
    for item in pricing_lines:
        if item["amount"] is not None:
            amount_html = f'<span class="price-amount">{format_currency(item["amount"])}</span>'
        else:
            amount_html = '<span class="price-amount price-incl">included</span>'
        rows.append(f"""
                <div class="price-row">
                    <span class="price-label">{item["label"]}</span>
                    {amount_html}
                </div>""")
    return "\n".join(rows)


def generate_testimonials_html(testimonials_text: str) -> str:
    """Generate testimonial cards HTML."""
    if not testimonials_text or not testimonials_text.strip():
        return ""

    cards = []
    # Split by blank lines or em-dash patterns
    blocks = [b.strip() for b in testimonials_text.split('\n\n') if b.strip()]
    if len(blocks) == 1:
        # Try splitting by — followed by newline
        blocks = [b.strip() for b in testimonials_text.split('\n') if b.strip()]

    for block in blocks[:3]:  # max 3 testimonials
        if not block:
            continue
        # Try to extract attribution
        match = re.search(r'—\s*(.+)$', block)
        if match:
            attribution = match.group(1).strip()
            quote = block[:match.start()].strip().strip('"')
        else:
            quote = block.strip().strip('"')
            attribution = "Verified Client"

        cards.append(f"""
            <div class="testimonial-card">
                <div class="testimonial-stars">★★★★★</div>
                <p class="testimonial-quote">"{quote}"</p>
                <p class="testimonial-attr">— {attribution}</p>
            </div>""")

    return "\n".join(cards)


def generate_guarantees_html(guarantees_text: str) -> str:
    """Generate guarantee badges HTML."""
    if not guarantees_text or not guarantees_text.strip():
        # Default guarantees
        guarantees = [
            "Price Lock Guarantee — your quote is your final price, no surprise charges",
            "Satisfaction Guarantee — we don't leave until you're happy with the result",
            "Clean Site Promise — your property is left clean at the end of every workday",
            "Reliability Guarantee — we show up when scheduled, every time",
        ]
    else:
        guarantees = [
            line.strip().lstrip('•-–—*').strip()
            for line in guarantees_text.splitlines()
            if line.strip()
        ]

    icons = ["🔒", "✅", "🌿", "📅", "⭐", "🛡️"]
    items = []
    for i, g in enumerate(guarantees[:6]):
        icon = icons[i % len(icons)]
        # Split on first colon or em dash to get title vs description
        if '—' in g or '-' in g:
            sep = '—' if '—' in g else '-'
            parts = g.split(sep, 1)
            title = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
        elif ':' in g:
            parts = g.split(':', 1)
            title = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
        else:
            title = g
            desc = ""

        items.append(f"""
            <div class="guarantee-item">
                <div class="guarantee-icon">{icon}</div>
                <div>
                    <div class="guarantee-title">{title}</div>
                    {f'<div class="guarantee-desc">{desc}</div>' if desc else ''}
                </div>
            </div>""")

    return "\n".join(items)


# ─────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_quote_html(job: dict) -> str:
    """
    Generate a complete HTML quote page from job dict.

    Required keys:
      contractor_name, company_name, client_name, project_address,
      scope_of_work, pricing_breakdown, total_price

    Optional keys:
      contractor_phone, contractor_email, contractor_bio,
      project_timeline, testimonials, guarantees_offered,
      brand_colors, logo_url, past_work_urls, notes
    """

    # Extract data
    contractor_name = job.get("contractor_name", "")
    company_name = job.get("company_name", "Your Contractor")
    client_name = job.get("client_name", "Valued Client")
    project_address = job.get("project_address", "")
    scope_text = job.get("scope_of_work", "")
    pricing_text = job.get("pricing_breakdown", "")
    total_price = job.get("total_price", 0)
    contractor_phone = job.get("contractor_phone", "")
    contractor_email = job.get("contractor_email", "")
    contractor_bio = job.get("contractor_bio", "")
    project_timeline = job.get("project_timeline", "")
    testimonials_text = job.get("testimonials", "")
    guarantees_text = job.get("guarantees_offered", "")
    job_id = job.get("job_id", "QUOTE001")
    date_str = datetime.now().strftime("%B %d, %Y")

    # Derived values
    dream_headline, dream_subtext = detect_dream_outcome(scope_text)
    scope_phases = split_scope_phases(scope_text)
    scope_story_html = generate_scope_story(scope_phases)
    pricing_lines = parse_pricing_lines(pricing_text)
    pricing_rows_html = generate_pricing_rows(pricing_lines, float(str(total_price).replace(',', '').replace('$', '')))
    testimonials_html = generate_testimonials_html(testimonials_text)
    guarantees_html = generate_guarantees_html(guarantees_text)

    total_formatted = format_currency(total_price)

    # Contact CTA
    if contractor_phone:
        phone_clean = re.sub(r'\D', '', contractor_phone)
        cta_href = f"tel:{phone_clean}"
        cta_label = f"Call {contractor_name} Now"
    elif contractor_email:
        cta_href = f"mailto:{contractor_email}?subject=Ready to Approve — {client_name} Project"
        cta_label = "Approve This Proposal"
    else:
        cta_href = "#contact"
        cta_label = "Approve This Proposal"

    # Timeline line
    timeline_line = f"<p class='timeline'>Estimated timeline: <strong>{project_timeline}</strong></p>" if project_timeline else ""

    # Bio section
    bio_section = ""
    if contractor_bio:
        bio_section = f'<p class="about-text">{contractor_bio}</p>'
    else:
        bio_section = f'<p class="about-text">{company_name} brings the expertise, professionalism, and attention to detail that your project deserves. Every job we take on becomes a showcase of what serious landscaping looks like.</p>'

    # Address display
    address_display = project_address.split(',')[0] if ',' in project_address else project_address

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{client_name} — Project Proposal by {company_name}</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    :root {{
      --green: #1B4332;
      --green-light: #2D6A4F;
      --green-pale: #40916C;
      --gold: #C9A84C;
      --gold-light: #E8C870;
      --dark: #0C0F18;
      --dark-card: #13172A;
      --dark-card2: #1A1E2E;
      --white: #FFFFFF;
      --white-dim: rgba(255,255,255,0.75);
      --white-muted: rgba(255,255,255,0.45);
      --border: rgba(255,255,255,0.07);
    }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--dark);
      color: var(--white);
      overflow-x: hidden;
    }}

    /* STICKY HEADER */
    .sticky-header {{
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      background: rgba(12,15,24,0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 14px 24px;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .sticky-logo {{ color: var(--gold); font-weight: 800; font-size: 16px; letter-spacing: 0.5px; }}
    .sticky-cta {{
      background: var(--green);
      color: var(--white);
      text-decoration: none;
      padding: 10px 22px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.3px;
      transition: background 0.2s;
    }}
    .sticky-cta:hover {{ background: var(--green-light); }}

    /* HERO */
    .hero {{
      min-height: 100vh;
      display: flex; flex-direction: column; justify-content: center;
      padding: 120px 24px 80px;
      background: linear-gradient(160deg, #0C0F18 0%, #0F1A12 60%, #1B4332 100%);
      position: relative; overflow: hidden;
    }}
    .hero::before {{
      content: '';
      position: absolute; inset: 0;
      background: radial-gradient(ellipse 60% 60% at 70% 40%, rgba(27,67,50,0.4) 0%, transparent 70%);
    }}
    .hero-inner {{ max-width: 780px; margin: 0 auto; position: relative; z-index: 1; }}
    .hero-badge {{
      display: inline-block;
      background: rgba(201,168,76,0.15);
      border: 1px solid rgba(201,168,76,0.3);
      color: var(--gold);
      font-size: 11px; font-weight: 700; letter-spacing: 2px;
      text-transform: uppercase; padding: 6px 16px; border-radius: 20px;
      margin-bottom: 28px;
      animation: fadeUp 0.6s ease both;
    }}
    .hero h1 {{
      font-family: 'Playfair Display', serif;
      font-size: clamp(36px, 7vw, 72px);
      line-height: 1.08;
      margin-bottom: 24px;
      animation: fadeUp 0.6s 0.1s ease both;
    }}
    .hero h1 em {{ color: var(--gold); font-style: normal; }}
    .hero-sub {{
      font-size: clamp(16px, 2.5vw, 20px);
      color: var(--white-dim);
      max-width: 560px;
      line-height: 1.6;
      margin-bottom: 40px;
      animation: fadeUp 0.6s 0.2s ease both;
    }}
    .hero-meta {{
      display: flex; gap: 24px; flex-wrap: wrap;
      animation: fadeUp 0.6s 0.3s ease both;
    }}
    .meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
    .meta-label {{ font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--gold); }}
    .meta-val {{ font-size: 14px; color: var(--white-dim); }}
    .hero-total {{
      margin-top: 48px;
      padding: 28px 32px;
      background: rgba(201,168,76,0.08);
      border: 1px solid rgba(201,168,76,0.2);
      border-radius: 12px;
      display: inline-flex; align-items: center; gap: 20px;
      animation: fadeUp 0.6s 0.35s ease both;
    }}
    .total-label {{ font-size: 12px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--white-muted); }}
    .total-amount {{ font-size: clamp(32px, 5vw, 48px); font-weight: 900; color: var(--gold); line-height: 1; }}

    /* SECTION BASE */
    .section {{ padding: 96px 24px; max-width: 860px; margin: 0 auto; }}
    .section-tag {{
      display: inline-block;
      background: rgba(27,67,50,0.5);
      border: 1px solid rgba(201,168,76,0.2);
      color: var(--gold);
      font-size: 10px; font-weight: 700; letter-spacing: 2px;
      text-transform: uppercase; padding: 5px 14px; border-radius: 20px;
      margin-bottom: 20px;
    }}
    .section h2 {{
      font-family: 'Playfair Display', serif;
      font-size: clamp(28px, 5vw, 48px);
      line-height: 1.15; margin-bottom: 16px;
    }}
    .section h2 em {{ color: var(--gold); font-style: normal; }}
    .section-intro {{ font-size: 17px; color: var(--white-dim); line-height: 1.7; max-width: 640px; margin-bottom: 48px; }}

    /* VISION SECTION */
    .vision-bg {{ background: linear-gradient(180deg, var(--dark) 0%, #0F1A12 100%); }}
    .vision-card {{
      background: var(--dark-card);
      border: 1px solid rgba(201,168,76,0.15);
      border-radius: 16px;
      padding: 40px;
    }}
    .vision-card p {{ font-size: 18px; line-height: 1.75; color: var(--white-dim); }}
    .vision-card strong {{ color: var(--white); }}

    /* SCOPE SECTION */
    .scope-item {{
      display: flex; gap: 20px; align-items: flex-start;
      padding: 24px 0;
      border-bottom: 1px solid var(--border);
    }}
    .scope-item:last-child {{ border-bottom: none; }}
    .scope-num {{
      flex-shrink: 0;
      width: 40px; height: 40px;
      background: rgba(27,67,50,0.6);
      border: 1px solid rgba(201,168,76,0.2);
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 13px; font-weight: 700; color: var(--gold); letter-spacing: 0.5px;
    }}
    .scope-text {{ font-size: 16px; color: var(--white-dim); line-height: 1.6; padding-top: 8px; }}

    /* SOCIAL PROOF / WHY US */
    .why-bg {{ background: #0F1A12; }}
    .about-text {{ font-size: 17px; color: var(--white-dim); line-height: 1.75; margin-bottom: 40px; max-width: 680px; }}
    .testimonials-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
    .testimonial-card {{
      background: var(--dark-card2);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 28px;
    }}
    .testimonial-stars {{ color: var(--gold); font-size: 14px; margin-bottom: 14px; letter-spacing: 2px; }}
    .testimonial-quote {{ font-size: 15px; color: var(--white-dim); line-height: 1.65; margin-bottom: 16px; font-style: italic; }}
    .testimonial-attr {{ font-size: 13px; color: var(--white-muted); font-weight: 600; }}

    /* PRICING */
    .pricing-bg {{ background: linear-gradient(180deg, #0C0F18 0%, #070a10 100%); }}
    .price-table {{
      background: var(--dark-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      margin-bottom: 24px;
    }}
    .price-row {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 18px 28px;
      border-bottom: 1px solid var(--border);
    }}
    .price-row:last-child {{ border-bottom: none; }}
    .price-label {{ font-size: 15px; color: var(--white-dim); }}
    .price-amount {{ font-size: 16px; font-weight: 700; color: var(--white); }}
    .price-incl {{ color: var(--green-pale); font-size: 13px; }}
    .price-total-row {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 24px 28px;
      background: rgba(27,67,50,0.3);
      border: 1px solid rgba(201,168,76,0.2);
      border-radius: 12px;
      margin-bottom: 12px;
    }}
    .price-total-label {{ font-size: 14px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--white-muted); }}
    .price-total-amount {{ font-size: 32px; font-weight: 900; color: var(--gold); }}
    .pricing-note {{ font-size: 13px; color: var(--white-muted); margin-top: 12px; }}

    /* GUARANTEES */
    .guarantees-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 40px; }}
    .guarantee-item {{
      display: flex; gap: 16px; align-items: flex-start;
      background: var(--dark-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
    }}
    .guarantee-icon {{ font-size: 22px; flex-shrink: 0; }}
    .guarantee-title {{ font-size: 14px; font-weight: 700; margin-bottom: 4px; }}
    .guarantee-desc {{ font-size: 13px; color: var(--white-muted); line-height: 1.5; }}

    /* CTA SECTION */
    .cta-section {{
      background: linear-gradient(135deg, #1B4332 0%, #0C0F18 100%);
      padding: 96px 24px;
      text-align: center;
    }}
    .cta-inner {{ max-width: 620px; margin: 0 auto; }}
    .cta-section h2 {{
      font-family: 'Playfair Display', serif;
      font-size: clamp(28px, 5vw, 44px);
      line-height: 1.2;
      margin-bottom: 16px;
    }}
    .cta-section h2 em {{ color: var(--gold); font-style: normal; }}
    .cta-section p {{ font-size: 17px; color: var(--white-dim); margin-bottom: 40px; line-height: 1.6; }}
    .cta-button {{
      display: inline-block;
      background: var(--gold);
      color: #0C0F18;
      text-decoration: none;
      padding: 18px 44px;
      border-radius: 8px;
      font-size: 16px; font-weight: 800;
      letter-spacing: 0.3px;
      transition: background 0.2s, transform 0.15s;
    }}
    .cta-button:hover {{ background: var(--gold-light); transform: translateY(-2px); }}
    .cta-sub {{ margin-top: 16px; font-size: 13px; color: var(--white-muted); }}

    /* FOOTER */
    .footer {{
      background: #070a10;
      padding: 32px 24px;
      text-align: center;
      border-top: 1px solid var(--border);
    }}
    .footer p {{ font-size: 13px; color: var(--white-muted); }}
    .footer .gc-badge {{
      display: inline-flex; align-items: center; gap: 8px;
      margin-top: 12px;
      font-size: 11px; color: var(--white-muted); letter-spacing: 0.5px;
    }}
    .footer .gc-badge strong {{ color: rgba(201,168,76,0.7); }}

    /* ANIMATIONS */
    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(24px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .fade-in {{ animation: fadeUp 0.6s ease both; }}

    /* RESPONSIVE */
    @media (max-width: 600px) {{
      .sticky-header {{ padding: 12px 16px; }}
      .sticky-cta {{ padding: 9px 16px; font-size: 12px; }}
      .section {{ padding: 64px 20px; }}
      .hero {{ padding: 100px 20px 64px; }}
      .hero-total {{ flex-direction: column; gap: 8px; padding: 20px 24px; }}
      .price-row {{ padding: 16px 20px; }}
      .vision-card {{ padding: 28px 24px; }}
    }}

    .timeline {{ margin-top: 20px; font-size: 15px; color: var(--white-muted); }}
    .timeline strong {{ color: var(--white-dim); }}
  </style>
</head>
<body>

  <!-- STICKY HEADER -->
  <header class="sticky-header">
    <div class="sticky-logo">{company_name}</div>
    <a href="{cta_href}" class="sticky-cta">{cta_label}</a>
  </header>

  <!-- HERO -->
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-badge">Proposal for {client_name} · {date_str}</div>
      <h1>{dream_headline.split(' — ')[0] if ' — ' in dream_headline else dream_headline}<br><em>for the {client_name.split()[-1]} Family</em></h1>
      <p class="hero-sub">This isn't a PDF. This is a complete project plan — built specifically for your {address_display} property — designed to show you exactly what's possible and why it's worth every dollar.</p>
      <div class="hero-meta">
        <div class="meta-item">
          <span class="meta-label">Prepared by</span>
          <span class="meta-val">{company_name}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Project address</span>
          <span class="meta-val">{project_address}</span>
        </div>
        {f'<div class="meta-item"><span class="meta-label">Timeline</span><span class="meta-val">{project_timeline}</span></div>' if project_timeline else ''}
      </div>
      <div class="hero-total">
        <div>
          <div class="total-label">Total Investment</div>
          <div class="total-amount">{total_formatted}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- VISION -->
  <section class="section vision-bg">
    <div class="section-inner">
      <div class="section-tag">Your Vision</div>
      <h2>Here's what we heard <em>you want.</em></h2>
      <p class="section-intro">We don't just take orders. We listen. Here's what stood out when we talked through your project.</p>
      <div class="vision-card">
        <p>You want <strong>{dream_subtext}</strong>. Not just to check a box on a to-do list — but to genuinely <strong>change how you feel about your property</strong>.</p>
        <br>
        <p>You've been looking at this space and imagining what it could be. It's time to stop imagining and start building. This proposal is exactly how we get there — step by step, with no surprises and no shortcuts.</p>
      </div>
    </div>
  </section>

  <!-- SCOPE OF WORK -->
  <section class="section">
    <div class="section-tag">The Work</div>
    <h2>Your project, <em>step by step.</em></h2>
    <p class="section-intro">Here's exactly what happens, in the order it happens — and why each step matters to the final result.</p>
    <div class="scope-list">
      {scope_story_html}
    </div>
    {timeline_line}
  </section>

  <!-- WHY US -->
  <section class="section why-bg">
    <div class="section-tag">Why {company_name}</div>
    <h2>The team <em>behind the work.</em></h2>
    {bio_section}
    {f'<div class="testimonials-grid">{testimonials_html}</div>' if testimonials_html else ''}
  </section>

  <!-- PRICING -->
  <section class="section pricing-bg">
    <div class="section-tag">Your Investment</div>
    <h2>Transparent pricing. <em>No surprises.</em></h2>
    <p class="section-intro">Every number below is locked in. What you see here is exactly what you pay — not a penny more.</p>
    <div class="price-table">
      {pricing_rows_html}
    </div>
    <div class="price-total-row">
      <span class="price-total-label">Total Project Investment</span>
      <span class="price-total-amount">{total_formatted}</span>
    </div>
    <p class="pricing-note">All materials, labor, permits (if required), and cleanup are included. No hidden fees.</p>

    <!-- GUARANTEES -->
    <div class="section-tag" style="margin-top:56px;">Our Guarantees</div>
    <h2>Your <em>peace of mind</em> is built in.</h2>
    <div class="guarantees-grid">
      {guarantees_html}
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-section">
    <div class="cta-inner">
      <h2>Ready to make <em>this real?</em></h2>
      <p>Your project is planned. Your investment is clear. The only thing left is to say yes.<br>Reach out now to lock in your start date before the schedule fills.</p>
      <a href="{cta_href}" class="cta-button">{cta_label} →</a>
      <p class="cta-sub">Questions? We'll respond same day.</p>
    </div>
  </section>

  <!-- FOOTER -->
  <footer class="footer">
    <p>This proposal was prepared exclusively for {client_name} by {company_name}.</p>
    <p>Reference: {job_id} · Prepared: {date_str}</p>
    <div class="gc-badge">Powered by <strong>GreenClose</strong> — Turn your quote into a closing machine</div>
  </footer>

  <script>
    // Fade-in on scroll
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{
        if (e.isIntersecting) {{
          e.target.classList.add('fade-in');
          observer.unobserve(e.target);
        }}
      }});
    }}, {{ threshold: 0.1 }});
    document.querySelectorAll('.section-tag, .vision-card, .scope-item, .testimonial-card, .price-table, .guarantee-item').forEach(el => observer.observe(el));
  </script>

</body>
</html>"""

    return html


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a GreenClose quote page from JSON data")
    parser.add_argument("--job_id", default="QUOTE001", help="Job ID (used in filename and footer)")
    parser.add_argument("--data", help="Path to JSON file with job data")
    parser.add_argument("--out", help="Output HTML path (default: frontend/quotes/{job_id}.html)")
    parser.add_argument("--demo", action="store_true", help="Generate a demo page with sample data")
    args = parser.parse_args()

    if args.demo:
        job = {
            "job_id": args.job_id,
            "contractor_name": "Marcus Rivera",
            "company_name": "Rivera Outdoor Living",
            "contractor_email": "marcus@riveraoutdoor.com",
            "contractor_phone": "(314) 555-0192",
            "contractor_bio": "15 years in landscaping, certified by the National Association of Landscape Professionals. Over 400 completed projects in the St. Louis metro area. We treat every yard like it's our own.",
            "client_name": "The Henderson Family",
            "project_address": "4821 Willow Creek Dr, Chesterfield, MO",
            "project_timeline": "4-5 weeks, beginning June 10th",
            "scope_of_work": """Remove existing dying grass and prepare soil (approx 2,400 sq ft)
Install premium Zoysia sod throughout backyard
Build a 400 sq ft natural flagstone patio with built-in seating wall
Install 6-zone irrigation system covering front and back yards
Plant 3 ornamental River Birch trees along property line for privacy
Add landscape lighting: 6 path lights, 4 uplights on trees, 2 spotlights
Grade the northwest corner to correct drainage issue causing standing water""",
            "pricing_breakdown": """Phase 1 — Foundation & Drainage: $3,200
Phase 2 — Flagstone Patio + Seating Wall: $8,400
Phase 3 — Sod Installation (2,400 sq ft Zoysia): $4,800
Phase 4 — Irrigation System (6 zones): $3,600
Phase 5 — Planting & Trees: $2,200
Phase 6 — Landscape Lighting: $2,800""",
            "total_price": 25000,
            "testimonials": """\"Marcus and his team completely transformed our yard. We went from embarrassed to show it off to hosting parties every weekend. Best investment we've made in the house.\" — The Kowalski Family, Wildwood MO

\"Professional from first call to final cleanup. Our irrigation system alone has saved us hours every week. These guys are the real deal.\" — Tom & Linda Marsh, Chesterfield MO""",
            "guarantees_offered": """60-Day Plant Survival Guarantee — we replace anything that doesn't take
Price Lock Guarantee — your quote is your final price, no surprise charges
Clean Site Promise — property left spotless at end of every workday
On-Time Guarantee — we show up when scheduled or we discount your invoice""",
        }
    elif args.data:
        with open(args.data) as f:
            job = json.load(f)
        job["job_id"] = args.job_id
    else:
        print("ERROR: provide --data <json_file> or use --demo")
        exit(1)

    html = generate_quote_html(job)

    out_path = args.out or f"frontend/quotes/{args.job_id}.html"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html)

    print(f"✅ Quote generated: {out_path}")
    print(f"   Job: {args.job_id} for {job.get('client_name', '?')}")
    print(f"   Total: {format_currency(job.get('total_price', 0))}")
