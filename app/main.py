#!/usr/bin/env python3
"""
GreenClose — FastAPI backend
Handles intake form submissions, triggers quote generation, manages job state.
"""

import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from .quote_generator import generate_quote_page
from .email_sender import send_quote_email, send_dennis_update
from .database import db
from .stripe_handler import create_checkout_session, verify_webhook, get_package_info

app = FastAPI(title="GreenClose API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated quote pages
QUOTES_DIR = Path(__file__).parent.parent / "frontend" / "quotes"
QUOTES_DIR.mkdir(parents=True, exist_ok=True)


class IntakeSubmission(BaseModel):
    # Contractor info
    contractor_name: str
    company_name: str
    contractor_email: str
    contractor_phone: Optional[str] = None
    brand_colors: Optional[str] = None  # e.g. "green and gold"
    logo_url: Optional[str] = None

    # Client info
    client_name: str
    client_email: str
    project_address: str

    # Project details
    scope_of_work: str          # Free text description of what's being done
    pricing_breakdown: str      # Line items with costs (text or structured)
    total_price: float
    project_timeline: Optional[str] = None  # e.g. "3-4 weeks, starting June 1"

    # Sales assets
    testimonials: Optional[str] = None
    past_work_urls: Optional[str] = None  # comma-separated
    guarantees_offered: Optional[str] = None
    contractor_bio: Optional[str] = None  # Why this contractor

    # Package type
    package: str = "first_win"  # first_win | closing_machine | market_dominator

    # Additional context
    notes: Optional[str] = None  # anything else Jeff should know


@app.get("/")
async def root():
    return {"status": "GreenClose is live", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/intake")
async def submit_intake(
    submission: IntakeSubmission,
    background_tasks: BackgroundTasks
):
    """
    Contractor submits their quote details.
    Returns a job ID immediately, generates quote in background.
    """
    job_id = str(uuid.uuid4())[:8].upper()

    # Save job to database
    job = {
        "id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "contractor_email": submission.contractor_email,
        "contractor_name": submission.contractor_name,
        "company_name": submission.company_name,
        "client_name": submission.client_name,
        "client_email": submission.client_email,
        "package": submission.package,
        "submission_data": submission.model_dump(),
    }

    await db.save_job(job)

    # Kick off generation in background
    background_tasks.add_task(process_quote_job, job_id, submission)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Got it! Your quote experience for {submission.client_name} is being generated. You'll receive it at {submission.contractor_email} within 48 hours.",
        "estimated_delivery": "Within 48 hours"
    }


async def process_quote_job(job_id: str, submission: IntakeSubmission):
    """Background task: generate quote page and email it to contractor."""
    try:
        await db.update_job_status(job_id, "generating")

        # Generate the HTML quote page
        # If Anthropic API key is not set, fall back to template generator
        if os.getenv("ANTHROPIC_API_KEY"):
            html_content = await generate_quote_page(job_id, submission)
        else:
            # Template fallback — produces quality output without Claude API
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from template_quote import generate_quote_html
            job_data = submission.model_dump()
            job_data["job_id"] = job_id
            html_content = generate_quote_html(job_data)
            print(f"[INFO] Job {job_id}: Used template generator (no ANTHROPIC_API_KEY)")

        # Save the HTML file
        quote_file = QUOTES_DIR / f"{job_id}.html"
        quote_file.write_text(html_content, encoding="utf-8")

        # Determine the quote URL
        base_url = os.getenv("BASE_URL", "https://greenclose.vercel.app")
        quote_url = f"{base_url}/q/{job_id}"

        await db.update_job_status(job_id, "delivered", quote_url=quote_url)

        # Email the contractor
        await send_quote_email(
            to_email=submission.contractor_email,
            contractor_name=submission.contractor_name,
            client_name=submission.client_name,
            job_id=job_id,
            quote_url=quote_url,
        )

    except Exception as e:
        await db.update_job_status(job_id, "error", error=str(e))
        print(f"[ERROR] Job {job_id} failed: {e}")


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Check status of a quote generation job."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "quote_url": job.get("quote_url"),
        "created_at": job.get("created_at"),
    }


@app.get("/q/{job_id}", response_class=HTMLResponse)
async def serve_quote(job_id: str):
    """Serve a generated quote page."""
    quote_file = QUOTES_DIR / f"{job_id}.html"
    if not quote_file.exists():
        raise HTTPException(status_code=404, detail="Quote not found")
    return HTMLResponse(content=quote_file.read_text(encoding="utf-8"))


@app.get("/api/stats")
async def get_stats():
    """Quick stats endpoint for Dennis updates."""
    stats = await db.get_stats()
    return stats


# ── Stripe Payment Endpoints ──────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    job_id: str
    package: str
    contractor_email: str


@app.post("/api/checkout")
async def create_checkout(req: CheckoutRequest):
    """
    Create a Stripe Checkout session for payment.
    Returns a redirect URL — send contractor there to pay.
    Requires STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in environment.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(
            status_code=503,
            detail="Payment system not yet configured. Please contact support."
        )

    base_url = os.getenv("BASE_URL", "https://greenclose.vercel.app")
    try:
        checkout_url = create_checkout_session(
            package=req.package,
            contractor_email=req.contractor_email,
            job_id=req.job_id,
            success_url=f"{base_url}/payment-success?job_id={req.job_id}",
            cancel_url=f"{base_url}/intake?cancelled=1",
        )
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    On checkout.session.completed — mark job as paid and trigger generation.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = verify_webhook(payload, sig_header)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        job_id = session.get("metadata", {}).get("job_id")
        if job_id:
            await db.update_job_status(job_id, "paid")
            # Trigger quote generation now that payment is confirmed
            job = await db.get_job(job_id)
            if job and job.get("submission_data"):
                submission = IntakeSubmission(**job["submission_data"])
                asyncio.create_task(process_quote_job(job_id, submission))

    return {"received": True}


@app.get("/payment-success")
async def payment_success(job_id: str):
    """Simple payment confirmation page."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Payment Confirmed — GreenClose</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0F1117; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }}
    .card {{ background: #1A1D27; border-radius: 12px; padding: 48px 40px; max-width: 480px; text-align: center; }}
    .check {{ width: 64px; height: 64px; background: #1B4332; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; font-size: 28px; }}
    h1 {{ color: #C9A84C; font-size: 28px; margin-bottom: 12px; }}
    p {{ color: rgba(255,255,255,0.7); line-height: 1.6; margin-bottom: 16px; }}
    .job-id {{ font-family: monospace; background: #0F1117; padding: 8px 16px; border-radius: 6px; font-size: 14px; color: #C9A84C; display: inline-block; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="check">✓</div>
    <h1>Payment Confirmed</h1>
    <p>Your quote experience is now in the queue. You'll receive an email with your personalized link within 48 hours.</p>
    <p style="font-size: 14px; color: rgba(255,255,255,0.5);">Reference:</p>
    <div class="job-id">Job #{job_id}</div>
    <p style="margin-top: 24px; font-size: 13px; color: rgba(255,255,255,0.4);">Questions? Reply to your confirmation email.</p>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)
