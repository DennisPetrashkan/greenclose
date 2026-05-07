#!/usr/bin/env python3
"""
GreenClose Stripe Payment Handler
Handles payment intent creation and webhook verification.
Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in environment to activate.
"""

import os
import json
from typing import Optional

# Pricing config — matches brand_decisions.md
PACKAGES = {
    "first_win": {
        "name": "First Win",
        "price_cents": 4900,  # $49
        "description": "1 quote experience, 48hr delivery, 1 revision",
        "quotes_per_month": 1,
    },
    "closing_machine": {
        "name": "Closing Machine",
        "price_cents": 19900,  # $199/mo
        "description": "10 quotes/month, 24hr delivery, unlimited revisions",
        "quotes_per_month": 10,
        "recurring": True,
        "interval": "month",
    },
    "market_dominator": {
        "name": "Market Dominator",
        "price_cents": 34900,  # $349/mo
        "description": "Unlimited quotes, priority 12hr delivery, phone support",
        "quotes_per_month": -1,  # unlimited
        "recurring": True,
        "interval": "month",
    },
}


def get_stripe():
    """Lazy-load stripe only when keys are present."""
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "STRIPE_SECRET_KEY not set. "
            "Go to stripe.com, create account, get API key, add to .env as STRIPE_SECRET_KEY=sk_live_..."
        )
    import stripe
    stripe.api_key = secret_key
    return stripe


def create_payment_intent(package: str, contractor_email: str, job_id: str) -> dict:
    """
    Create a Stripe PaymentIntent for a one-time quote purchase.
    Returns client_secret for frontend to complete payment.
    """
    stripe = get_stripe()
    pkg = PACKAGES.get(package)
    if not pkg:
        raise ValueError(f"Unknown package: {package}. Must be one of: {list(PACKAGES.keys())}")

    intent = stripe.PaymentIntent.create(
        amount=pkg["price_cents"],
        currency="usd",
        metadata={
            "job_id": job_id,
            "package": package,
            "contractor_email": contractor_email,
        },
        receipt_email=contractor_email,
        description=f"GreenClose {pkg['name']} — Job {job_id}",
    )

    return {
        "client_secret": intent.client_secret,
        "amount": pkg["price_cents"],
        "package_name": pkg["name"],
        "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
    }


def create_checkout_session(package: str, contractor_email: str, job_id: str, success_url: str, cancel_url: str) -> str:
    """
    Create a Stripe Checkout Session (hosted payment page — no Stripe.js needed).
    Returns the checkout URL to redirect contractor to.
    This is the simplest integration — just redirect to the URL.
    """
    stripe = get_stripe()
    pkg = PACKAGES.get(package)
    if not pkg:
        raise ValueError(f"Unknown package: {package}")

    session_params = {
        "payment_method_types": ["card"],
        "customer_email": contractor_email,
        "line_items": [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"GreenClose {pkg['name']}",
                        "description": pkg["description"],
                    },
                    "unit_amount": pkg["price_cents"],
                },
                "quantity": 1,
            }
        ],
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "job_id": job_id,
            "package": package,
            "contractor_email": contractor_email,
        },
    }

    session = stripe.checkout.Session.create(**session_params)
    return session.url


def verify_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    """
    Verify and parse a Stripe webhook event.
    Returns the event dict if valid, None if invalid.
    """
    stripe = get_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return event
    except stripe.error.SignatureVerificationError:
        return None


def get_package_info(package: str) -> dict:
    """Return package details for display."""
    return PACKAGES.get(package, PACKAGES["first_win"])
