# 🚀 Deploy ResumRank AI Live (Free)

## What You'll Get
- Live URL: https://resumrank-ai.up.railway.app (or custom domain)
- Zero API costs: users bring their own Gemini key
- Free tier: Railway gives 500 hours/month free
- Total cost: $0

## Prerequisites
- A GitHub account
- The project pushed to a GitHub repository
- A Railway account (free, sign in with GitHub)

## Step 1: Push to GitHub (5 minutes)

```bash
git init
git add .
git commit -m "feat: initial deployment setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Do NOT commit:
- .env
- uploads/
- results/
- test_data/*.pdf

Quick check:
- Confirm .gitignore includes .env, uploads/, results/, and test_data/.

## Step 2: Deploy on Railway (5 minutes)

1. Go to https://railway.app and click New Project
2. Select Deploy from GitHub
3. Choose your ResumRank AI repository
4. Railway auto-detects Python + Procfile
5. Watch the build logs until it says Deploy Successful

## Step 3: Set Environment Variables on Railway (2 minutes)

1. Open your Railway project
2. Click your service, then go to Variables
3. Add the following:

```
APP_ENV=production
SECRET_KEY=click "Generate"
```

Do NOT add GEMINI_API_KEY — users bring their own.

## Step 4: Verify Deployment

1. Visit the live URL shown in Railway
2. Test the health endpoint:
   - https://YOUR-APP.up.railway.app/health
3. Upload a test resume using a real Gemini API key

## Step 5: Custom Domain (Optional)

1. Railway Settings → Domains → Add custom domain
2. Point your DNS CNAME to Railway
3. Wait for DNS to propagate

## Troubleshooting

- Build fails: confirm requirements.txt includes gunicorn==21.2.0
- App crashes on start: make sure PORT is handled by the app
- Gemini errors: user key is required in the UI
- Upload timeouts: gunicorn timeout is set to 120 seconds

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| APP_ENV | Yes | Set to "production" |
| SECRET_KEY | Yes | Random string for Flask sessions |
| PORT | Auto | Set by Railway automatically |
| GEMINI_API_KEY | No | Provided by users in the UI |

## Troubleshooting FAQ

Q: The app deploys but shows a 500 error on the homepage. What should I check?
A: Verify the Railway build logs, confirm requirements.txt has all dependencies, and check that the /health endpoint returns 200.

Q: Upload fails with "API key required" even after entering a key.
A: Confirm the frontend sends api_key in both /upload and /analyze, and that the input length is at least 20 characters.

Q: Why are results lost after a redeploy?
A: Railway uses ephemeral storage. In-memory sessions reset on restart by design. For persistence, move results to a database.

Q: Is it safe to enter a Gemini API key?
A: The key is sent directly to Google via your server and is not stored or logged. You can verify this in the source code.
