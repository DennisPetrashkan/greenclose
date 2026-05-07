# Deploy GreenClose in 10 Minutes

This document gets the site live on Render.com. Do this first before anything else.
No coding required. Follow each step exactly.

---

## Step 1 — Push Code to GitHub (2 min)

Open Terminal in this folder and run:
```
git add -A
git commit -m "GreenClose MVP ready to deploy"
git push
```

If you don't have a GitHub account, create one at github.com, then create a new repo called `greenclose`, and run:
```
git remote add origin https://github.com/YOUR_USERNAME/greenclose.git
git push -u origin main
```

---

## Step 2 — Deploy on Render (5 min)

1. Go to **render.com** and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account → select the `greenclose` repo
4. Render auto-detects the settings from `render.yaml`
5. Click **"Create Web Service"**

That's it. Render builds and deploys automatically.

---

## Step 3 — Add Environment Variables (3 min)

In Render dashboard → your service → **"Environment"** tab:

Add these:
```
ANTHROPIC_API_KEY = sk-ant-YOUR_KEY_HERE
GMAIL_APP_PASSWORD = cmzcygojcvdmhzro
STRIPE_SECRET_KEY = sk_live_YOUR_KEY_HERE
STRIPE_PUBLISHABLE_KEY = pk_live_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET = whsec_YOUR_KEY_HERE
```

(Only ANTHROPIC_API_KEY and GMAIL_APP_PASSWORD are required for basic operation)

---

## After Deployment

Your site is live at: **https://greenclose.onrender.com**

Test it:
- Visit https://greenclose.onrender.com — should show `{"status":"GreenClose is live"}`
- Visit https://greenclose.onrender.com/q/DEMO001 — should show the demo quote page
- Visit https://greenclose.onrender.com/intake — should show the intake form

---

## What Each Key Does

| Key | Required For | Get It At |
|-----|-------------|-----------|
| ANTHROPIC_API_KEY | Generating quote pages | console.anthropic.com |
| GMAIL_APP_PASSWORD | Sending emails | Already set — cmzcygojcvdmhzro |
| STRIPE_SECRET_KEY | Taking payment | stripe.com |
| STRIPE_PUBLISHABLE_KEY | Payment form | stripe.com |
| STRIPE_WEBHOOK_SECRET | Confirming payment | stripe.com → Webhooks |

**Without Anthropic key:** Site runs, demo works, intake works, but quotes generate with placeholder content.
**Without Stripe keys:** Site runs, intake works, but payment step is skipped.
