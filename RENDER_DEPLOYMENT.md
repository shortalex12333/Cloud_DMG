# 🚀 Render Deployment Guide

**Repository:** https://github.com/shortalex12333/Cloud_DMG
**Branch:** `python-implementation`
**Status:** ✅ Ready to deploy

---

## 📋 Quick Deploy Checklist

- [x] Code pushed to GitHub (python-implementation branch)
- [x] Requirements.txt configured
- [x] Health check endpoint (/health) implemented
- [x] Environment variables documented
- [ ] Create Render Web Service
- [ ] Configure environment variables
- [ ] Deploy and test

---

## 🚀 Step 1: Create New Web Service on Render

### Go to Render Dashboard

1. Visit: https://dashboard.render.com/
2. Click "New +" → "Web Service"

### Connect GitHub Repository

1. **Repository:** `shortalex12333/Cloud_DMG`
2. Click "Connect"
3. **Branch:** `python-implementation`

---

## ⚙️ Step 2: Configure Web Service

### Basic Settings

| Field | Value |
|-------|-------|
| **Name** | `celesteos-cloud-onboarding` |
| **Region** | Oregon (US West) or your preference |
| **Branch** | `python-implementation` |
| **Root Directory** | (leave empty - code is in root) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

### Advanced Settings

| Field | Value |
|-------|-------|
| **Instance Type** | Free (or Starter $7/month for production) |
| **Health Check Path** | `/health` |
| **Auto-Deploy** | ✅ Yes (deploys on push to python-implementation) |

---

## 🔐 Step 3: Add Environment Variables

In Render Dashboard → Environment tab, add these variables:

### Database Variables
```bash
SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw
```

### Azure Email Variables
```bash
AZURE_TENANT_ID=073af86c-74f3-422b-ad5c-a35d41fce4be
AZURE_CLIENT_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
AZURE_CLIENT_SECRET=<your-azure-client-secret>
```

**Note:** Get the full Azure client secret from your local `.env` file or Azure Portal.

### Email Configuration
```bash
SENDER_EMAIL=contact@celeste7.ai
SENDER_NAME=Celeste7 Yacht Onboarding
```

### Server Configuration
```bash
HOST=0.0.0.0
PORT=10000
API_BASE_URL=https://api.celeste7.ai
```

**Note:** Render automatically sets `PORT` environment variable. You can override it if needed.

---

## 🎯 Step 4: Deploy

1. Click "Create Web Service"
2. Render will:
   - Clone the repository
   - Run `pip install -r requirements.txt`
   - Start server with `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Wait 2-3 minutes for deployment

**Deployment URL will be:** `https://celesteos-cloud-onboarding.onrender.com` (or similar)

---

## ✅ Step 5: Verify Deployment

### Test Health Endpoint
```bash
curl https://celesteos-cloud-onboarding.onrender.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "celeste7-cloud"
}
```

### Test Root Endpoint
```bash
curl https://celesteos-cloud-onboarding.onrender.com/
```

**Expected response:**
```json
{
  "service": "CelesteOS Cloud API",
  "version": "1.0.0",
  "endpoints": {
    "register": "POST /webhook/register",
    "check_activation": "POST /webhook/check-activation/:yacht_id",
    "activate": "GET /webhook/activate/:yacht_id"
  }
}
```

### Test API Docs
Visit: `https://celesteos-cloud-onboarding.onrender.com/docs`

Should see FastAPI Swagger UI with all endpoints documented.

---

## 🔧 Step 6: Configure Custom Domain (Optional)

### If you want to use api.celeste7.ai:

1. **In Render Dashboard:**
   - Go to your service → Settings → Custom Domain
   - Click "Add Custom Domain"
   - Enter: `api.celeste7.ai`

2. **In your DNS provider (Cloudflare/etc):**
   - Add CNAME record:
     ```
     Type: CNAME
     Name: api
     Value: celesteos-cloud-onboarding.onrender.com
     ```
   - Or use Render's provided DNS values

3. **Wait for DNS propagation** (5-30 minutes)

4. **Update API_BASE_URL:**
   - In Render Dashboard → Environment
   - Update: `API_BASE_URL=https://api.celeste7.ai`
   - Service will auto-redeploy

---

## 🧪 Step 7: Test End-to-End

### Test Email Sending
```bash
curl -X POST https://celesteos-cloud-onboarding.onrender.com/webhook/register \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "RENDER_TEST_001",
    "yacht_id_hash": "abc123def456..."
  }'
```

**Note:** You'll need a real yacht in the database for this to work.

### Check Logs
In Render Dashboard → Logs tab:
```
[EMAIL] ✅ Sent to buyer@example.com
✅ Registration successful!
```

---

## 🔍 Monitoring & Debugging

### View Logs
- **Dashboard:** Render Dashboard → Logs tab
- **Real-time:** Click "Logs" to see live stream

### Health Check
Render automatically pings `/health` every few minutes to ensure service is running.

### Restart Service
If needed: Render Dashboard → Manual Deploy → "Clear build cache & deploy"

---

## ⚡ Performance Notes

### Free Tier Limitations
- **Spins down after 15 minutes** of inactivity
- **Cold start:** 30-60 seconds on first request
- **Shared resources**

### Upgrade to Starter ($7/month) for:
- ✅ Always-on (no spin down)
- ✅ Faster response times
- ✅ More memory/CPU
- ✅ Better for production

---

## 🚨 Troubleshooting

### Issue: Build fails
**Check:**
- `requirements.txt` exists in root
- All dependencies are valid Python packages

### Issue: Service won't start
**Check:**
- `PORT` environment variable is set
- Start command is correct: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Check logs for Python errors

### Issue: 502 Bad Gateway
**Cause:** Service crashed or didn't start
**Fix:** Check logs for errors, verify environment variables

### Issue: Email not sending
**Check:**
- Azure credentials in environment variables
- Check logs for `[EMAIL]` messages
- Verify Microsoft Graph API credentials

### Issue: Database connection fails
**Check:**
- Supabase credentials in environment variables
- Supabase project is active
- Network connectivity from Render to Supabase

---

## 📊 Expected Deployment Flow

```
1. Push to GitHub (python-implementation branch)
   ↓
2. Render detects push (auto-deploy enabled)
   ↓
3. Render clones repository
   ↓
4. Runs: pip install -r requirements.txt
   ↓
5. Starts: uvicorn main:app --host 0.0.0.0 --port $PORT
   ↓
6. Service available at: https://your-app.onrender.com
   ↓
7. Health check passes: GET /health → 200 OK
   ↓
8. ✅ Service is LIVE
```

---

## 🎯 Post-Deployment Checklist

- [ ] Health endpoint returns 200 OK
- [ ] Root endpoint returns API info
- [ ] API docs accessible at /docs
- [ ] Test registration with real yacht
- [ ] Verify email sending works
- [ ] Check database operations
- [ ] Monitor logs for errors
- [ ] Set up custom domain (optional)
- [ ] Consider upgrading to Starter tier

---

## 📧 Webhook URLs After Deployment

Once deployed, your webhooks will be:

```
Registration:
POST https://celesteos-cloud-onboarding.onrender.com/webhook/register

Check Activation:
POST https://celesteos-cloud-onboarding.onrender.com/webhook/check-activation/:yacht_id

Activation (Email Link):
GET https://celesteos-cloud-onboarding.onrender.com/webhook/activate/:yacht_id
```

**Or with custom domain:**
```
POST https://api.celeste7.ai/webhook/register
POST https://api.celeste7.ai/webhook/check-activation/:yacht_id
GET https://api.celeste7.ai/webhook/activate/:yacht_id
```

---

## 🔐 Security Checklist

- [x] Secrets stored as environment variables (not in code)
- [x] `.env` file in `.gitignore` (secrets not committed)
- [x] HTTPS enabled by default on Render
- [x] Input validation with Pydantic
- [x] XSS protection (HTML escaping)
- [x] One-time credential retrieval enforced

---

## 💰 Cost

**Free Tier:**
- ✅ Free forever
- ⚠️ Spins down after 15 min inactivity
- ⚠️ 750 hours/month limit (shared across all free services)

**Starter Tier ($7/month):**
- ✅ Always-on
- ✅ Better performance
- ✅ Recommended for production

---

## 📞 Support

**Render Documentation:** https://render.com/docs
**Render Status:** https://status.render.com
**Support:** dashboard.render.com (chat support)

---

## ✅ Ready to Deploy?

All code is ready on branch: `python-implementation`

Just follow steps 1-4 above and you'll be live in ~5 minutes! 🚀
