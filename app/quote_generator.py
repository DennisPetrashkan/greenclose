#!/usr/bin/env python3
"""
GreenClose Quote Generator
Uses Claude API to produce a fully interactive HTML quote experience
based on the contractor's submission data.
"""

import os
import anthropic
from pathlib import Path
from datetime import datetime

# Client is initialized from env var ANTHROPIC_API_KEY
_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are GreenClose's quote experience engine. You transform raw landscaping contractor quote data into stunning, persuasive interactive HTML pages that close deals.

Your output is a COMPLETE, standalone HTML file — no imports, no external dependencies except Google Fonts and a CDN-hosted animation library if needed. Everything must be self-contained.

## Sales Psychology You Must Apply (Hormozi Framework)

Value Equation: Value = (Dream Outcome × Likelihood of Achievement) ÷ (Time Delay × Effort)

1. Lead with the homeowner's DREAM OUTCOME — not the contractor's services
2. Show CREDIBILITY before showing price
3. Lower perceived TIME and EFFORT — make the process feel effortless
4. Multiple micro-yeses before price lands
5. Always present pricing as tiers or phases — never a single number
6. Name packages after outcomes, not tiers

## Design Requirements (Non-Negotiable)

- Mobile-first. Looks perfect on a 375px iPhone screen.
- Default palette if no brand colors: #1B4332 (forest green) + #C9A84C (gold) + #FFFFFF + #0F1117
- If brand colors provided, use them throughout
- Clean, premium, high-end feel — think luxury service, not contractor website
- Smooth scroll behavior, subtle entrance animations using CSS only (no external JS libraries)
- Dark/light alternating sections for visual rhythm
- Large, bold emotional headlines — homeowner should feel something in 5 seconds
- Interactive pricing section — use CSS checkboxes/radio buttons for toggles (no external JS needed)
- One clear call-to-action at the end
- NO lorem ipsum. Every word must be specific to this project.

## Required Sections (in order)

1. **Hero** — Contractor logo/name + emotional headline targeting homeowner's dream outcome
2. **Vision** — "Here's what we heard you want" — reflect their actual project back in vivid language
3. **The Work** — Scope presented as a story/journey, NOT line items. What happens first, then next, then the result.
4. **Why [Contractor Name]** — Credibility section: testimonials if provided, guarantees, credentials, selectivity signal
5. **Your Investment** — Interactive pricing with phases or options. Premium tier anchors first.
6. **Next Step** — Single, specific CTA. Reserve your slot / Approve this proposal / etc.

## HTML Structure Rules

- Use semantic HTML5
- Inline all CSS in a <style> tag in <head>
- Use vanilla JS only, minimal, inline in <script> at end of body
- Interactive pricing: use <input type="checkbox"> or <input type="radio"> with CSS :checked selectors to show/hide pricing tiers or add-ons
- Smooth scroll: add `scroll-behavior: smooth` to html element
- Entrance animations: use @keyframes + CSS animation-delay staggering
- Include a sticky header with contractor name + "Approve Proposal" CTA button

Output ONLY the complete HTML file. No preamble, no explanation, no markdown code fences. Start with <!DOCTYPE html> and end with </html>."""


def build_prompt(job_id: str, submission) -> str:
    """Build the user prompt from submission data."""

    lines = [
        f"JOB ID: {job_id}",
        f"DATE: {datetime.utcnow().strftime('%B %d, %Y')}",
        "",
        "=== CONTRACTOR INFO ===",
        f"Contractor: {submission.contractor_name}",
        f"Company: {submission.company_name}",
        f"Email: {submission.contractor_email}",
    ]

    if submission.contractor_phone:
        lines.append(f"Phone: {submission.contractor_phone}")
    if submission.brand_colors:
        lines.append(f"Brand Colors: {submission.brand_colors}")
    if submission.logo_url:
        lines.append(f"Logo URL: {submission.logo_url}")
    if submission.contractor_bio:
        lines.append(f"Contractor Bio/About: {submission.contractor_bio}")

    lines += [
        "",
        "=== CLIENT & PROJECT ===",
        f"Homeowner Name: {submission.client_name}",
        f"Project Address: {submission.project_address}",
    ]

    if submission.project_timeline:
        lines.append(f"Timeline: {submission.project_timeline}")

    lines += [
        "",
        "=== SCOPE OF WORK ===",
        submission.scope_of_work,
        "",
        "=== PRICING BREAKDOWN ===",
        submission.pricing_breakdown,
        f"Total Investment: ${submission.total_price:,.2f}",
    ]

    if submission.testimonials:
        lines += ["", "=== TESTIMONIALS ===", submission.testimonials]

    if submission.past_work_urls:
        lines += ["", "=== PAST WORK / PORTFOLIO URLS ===", submission.past_work_urls]

    if submission.guarantees_offered:
        lines += ["", "=== GUARANTEES OFFERED ===", submission.guarantees_offered]

    if submission.notes:
        lines += ["", "=== ADDITIONAL NOTES ===", submission.notes]

    lines += [
        "",
        "=== PACKAGE ===",
        submission.package,
        "",
        "Now generate the complete, standalone HTML quote experience page for this project.",
        "Make it stunning. Make it personal. Make it close deals.",
        "The homeowner's name is " + submission.client_name + " — use it naturally throughout.",
        "The contractor's company is " + submission.company_name + " — this is their brand you're amplifying.",
    ]

    return "\n".join(lines)


async def generate_quote_page(job_id: str, submission) -> str:
    """
    Generate a complete HTML quote experience using Claude.
    Returns the full HTML string.
    """
    client = get_client()

    prompt = build_prompt(job_id, submission)

    # Use claude-sonnet-4-6 for quality — this is the core product value
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    html = message.content[0].text.strip()

    # Sanity check — make sure we got actual HTML
    if not html.startswith("<!DOCTYPE") and not html.startswith("<html"):
        # Claude sometimes adds a preamble — strip to first HTML tag
        idx = html.find("<!DOCTYPE")
        if idx == -1:
            idx = html.find("<html")
        if idx != -1:
            html = html[idx:]
        else:
            raise ValueError(f"Claude did not return valid HTML for job {job_id}")

    return html


async def generate_demo_page(job_id: str = "DEMO001") -> str:
    """
    Generate a demo quote page with fictional data for sales/marketing purposes.
    """
    from types import SimpleNamespace

    demo = SimpleNamespace(
        contractor_name="Marcus Rivera",
        company_name="Rivera Outdoor Living",
        contractor_email="marcus@riveraoutdoor.com",
        contractor_phone="(314) 555-0192",
        brand_colors="deep green and brushed gold",
        logo_url=None,
        contractor_bio="15 years in landscaping, certified by the National Association of Landscape Professionals, over 400 completed projects in the St. Louis metro area.",
        client_name="The Henderson Family",
        client_email="henderson@email.com",
        project_address="4821 Willow Creek Dr, Chesterfield, MO 63017",
        project_timeline="4-5 weeks, beginning June 10th",
        scope_of_work="""
Complete backyard transformation including:
- Remove existing dying grass and prepare soil (approx 2,400 sq ft)
- Install premium Zoysia sod throughout backyard
- Build a 400 sq ft natural flagstone patio with built-in seating wall
- Install 6-zone irrigation system covering front and back yards
- Plant 3 ornamental trees (River Birch) along property line for privacy
- Add landscape lighting: 6 path lights, 4 uplights on trees, 2 spotlight fixtures
- Grade the northwest corner to correct drainage issue causing standing water
        """.strip(),
        pricing_breakdown="""
Phase 1 — Foundation (Grading, Drainage, Soil Prep): $3,200
Phase 2 — Hardscape (Flagstone Patio + Seating Wall): $8,400
Phase 3 — Sod Installation (2,400 sq ft Zoysia): $4,800
Phase 4 — Irrigation System (6 zones): $3,600
Phase 5 — Planting + Trees: $2,200
Phase 6 — Landscape Lighting: $2,800
Optional Add-On: Pergola over patio seating area: +$4,500
        """.strip(),
        total_price=25000,
        testimonials="""
"Marcus and his team completely transformed our yard. We went from embarrassed to show it off to hosting parties every weekend. Best investment we've made in the house." — The Kowalski Family, Wildwood MO

"Professional from first call to final cleanup. Our irrigation system alone has saved us hours every week. These guys are the real deal." — Tom & Linda Marsh, Chesterfield MO
        """.strip(),
        past_work_urls="https://riveraoutdoor.com/portfolio",
        guarantees_offered="""
- 60-Day Plant Survival Guarantee (we replace anything that doesn't take)
- Price Lock Guarantee (your quote is your price — no surprise charges)
- Cleanup Guarantee (site left spotless at end of each workday)
- On-Time Guarantee (we show up when scheduled or we discount your invoice)
        """.strip(),
        package="closing_machine",
        notes="The Hendersons mentioned their daughter's graduation party is July 15th — they want the yard ready before then. This is a strong close motivator.",
    )

    return await generate_quote_page(job_id, demo)
