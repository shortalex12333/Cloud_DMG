# ✅ Azure Graph API Setup - CelesteOS.Outlook.Write

**App:** CelesteOS.Outlook.Write
**Status:** ✅ Has Mail.Send Application permission - Ready to send emails!
**Date:** 2026-01-07

---

## 🎯 What You Need to Do (2 minutes)

### Step 1: Get the Full Client Secret

You have 2 secrets available:
- **"WRITE"** (expires 09/03/2027): `MSq******************`
- **"Oct-2025"** (expires 27/10/2027): `K8F******************`

**To reveal the full secret:**
1. Go to Azure Portal: https://portal.azure.com
2. Azure AD > App registrations > CelesteOS.Outlook.Write
3. Certificates & secrets > Client secrets
4. Click the copy icon next to either secret to copy the full value

**Note:** If the full secret isn't visible (only shows `***`), you'll need to create a new secret:
- Click "New client secret"
- Description: "CelesteOS Cloud Onboarding"
- Expires: 24 months
- Click "Add"
- **IMMEDIATELY copy the Value** (it only shows once!)

### Step 2: Add Secret to .env

Open `.env` file and update line 16:
```bash
# Change this:
# AZURE_CLIENT_SECRET=<paste-full-secret-here>

# To this:
AZURE_CLIENT_SECRET=MSq8Q~your_full_secret_value_here
```

Remove the `#` at the start and paste the full secret after `=`

### Step 3: Test Email Sending

```bash
cd /Users/celeste7/Documents/CelesteOS-Cloud-Python
python3 test_email_sending.py
```

**Expected output:**
```
✅ Email sent successfully!
   Check shortalex@hotmail.co.uk for the test email
```

### Step 4: Run Full Tests

```bash
python3 test_until_perfect.py
```

**Expected output:**
```
[EMAIL] ✅ Sent to <email>
✅ YACHT #1 PASSED PERFECTLY!
```

---

## 📋 Current Configuration

**Azure App Details:**
```
App Name: CelesteOS.Outlook.Write
Tenant ID: 073af86c-74f3-422b-ad5c-a35d41fce4be
Client ID: f0b8944b-8127-4f0f-8ed5-5487462df50c
Client Secret: <waiting for you to add to .env>
```

**Permissions (✅ Already Granted):**
- ✅ Mail.Send (Application) - **This is what we need!**
- ✅ Mail.ReadWrite (Delegated)
- ✅ Mail.Send (Delegated)
- ✅ Mail.Send.Shared (Delegated)
- Plus 11 other permissions

**Admin Consent:** ✅ Granted for CELESTE7 LTD

---

## 🔧 .env Configuration

**Current (in `.env`):**
```bash
AZURE_TENANT_ID=073af86c-74f3-422b-ad5c-a35d41fce4be
AZURE_CLIENT_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
# AZURE_CLIENT_SECRET=<paste-full-secret-here>  # ← UNCOMMENT AND FILL THIS
SENDER_EMAIL=shortalex@hotmail.co.uk
SENDER_NAME=Celeste7 Yacht Onboarding
```

**After you add the secret:**
```bash
AZURE_TENANT_ID=073af86c-74f3-422b-ad5c-a35d41fce4be
AZURE_CLIENT_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
AZURE_CLIENT_SECRET=MSq8Q~your_full_secret_value_here
SENDER_EMAIL=shortalex@hotmail.co.uk
SENDER_NAME=Celeste7 Yacht Onboarding
```

---

## ✅ Why This Will Work

### Mail.Send Application Permission ✅
- **What it means:** The app can send emails as ANY user in your tenant
- **How it works:** Uses client credentials (app ID + secret) to authenticate
- **No user interaction:** Sends emails without requiring user login
- **Status:** ✅ Already granted admin consent

### Correct App Configuration
- **App type:** Multi-organization (can be used in your tenant)
- **Client credentials:** 2 secrets available
- **Permissions:** Already granted and consented
- **Sender:** shortalex@hotmail.co.uk (must exist in your tenant)

---

## 🎯 Expected Email Behavior

### With Secret (Microsoft Graph API):
```
[EMAIL] ✅ Sent to buyer@example.com
✅ Registration successful!
```

### Without Secret (Fallback):
```
[EMAIL] Graph API failed: Missing AZURE_CLIENT_SECRET
[EMAIL] ⚠️ Failed to send: No email service configured
[EMAIL] Activation Link (manual): https://...
✅ Registration successful!
```

---

## 🚀 After Adding Secret

Run these commands to verify everything works:

```bash
# 1. Test email sending
python3 test_email_sending.py

# 2. Check inbox for test email
# Look for email from: Celeste7 Yacht Onboarding <shortalex@hotmail.co.uk>
# Subject: Test: Yacht Activation Email

# 3. Run full autonomous tests
python3 test_until_perfect.py

# 4. Verify yacht #1 passes with email sent
# Look for: [EMAIL] ✅ Sent to itertest1@celeste7.ai
```

---

## 📧 Email Sending Details

**How it works:**
1. Gets OAuth token using client credentials (tenant ID + client ID + secret)
2. Calls Microsoft Graph API: `POST /users/{sender}/sendMail`
3. Sends HTML email from shortalex@hotmail.co.uk
4. Email includes activation button and link

**What buyers receive:**
- From: Celeste7 Yacht Onboarding <shortalex@hotmail.co.uk>
- Subject: Activate Your Yacht: YACHT_ID
- Professional HTML email with button
- Plain text fallback

---

## 🔍 Troubleshooting

### Issue: "Sender email not found"
**Solution:** Make sure shortalex@hotmail.co.uk exists in your Microsoft tenant

### Issue: "Token acquisition failed"
**Solution:** Check that AZURE_CLIENT_SECRET is uncommented and has the full secret value

### Issue: "Forbidden (403)"
**Solution:** Verify Mail.Send permission is granted and admin consent is given

---

## 📊 Summary

**Status:** Ready to send emails with Microsoft Graph API
**What's needed:** Add AZURE_CLIENT_SECRET to .env (2-minute task)
**What happens:** Automatic professional email sending from shortalex@hotmail.co.uk

**Next step:** Copy the client secret value and add it to `.env`

---

**Azure Portal:** https://portal.azure.com
**App:** CelesteOS.Outlook.Write (f0b8944b-8127-4f0f-8ed5-5487462df50c)
**Secrets Location:** App registrations > Certificates & secrets
