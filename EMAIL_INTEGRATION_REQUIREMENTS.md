# Email Integration Requirements

To implement actual email sending, I need configuration details. Here are the options:

---

## Option 1: Microsoft Graph API (Recommended)
**Best for:** Office 365 / Microsoft 365 accounts

### Required Information:
1. **Azure AD App Registration**
   - Tenant ID (Azure AD tenant)
   - Client ID (Application/App ID)
   - Client Secret (App password)

2. **Email Account**
   - Sender email address (e.g., noreply@celeste7.ai)

3. **API Permissions** (must be configured in Azure Portal)
   - `Mail.Send` (Application permission)

### How to Get These:
```
1. Go to: https://portal.azure.com
2. Navigate to: Azure Active Directory > App registrations > New registration
3. Create app: "CelesteOS-Yacht-Onboarding"
4. Copy: Application (client) ID
5. Copy: Directory (tenant) ID
6. Create secret: Certificates & secrets > New client secret
7. Copy: Secret value (only shown once!)
8. Add permissions: API permissions > Microsoft Graph > Application permissions > Mail.Send
9. Admin consent: Click "Grant admin consent"
```

### What I Need From You:
```
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=noreply@celeste7.ai
```

---

## Option 2: SMTP (Office 365)
**Best for:** If you already have Office 365 email

### Required Information:
1. **SMTP Server:** smtp.office365.com
2. **Port:** 587 (TLS)
3. **Email:** Your Office 365 email (e.g., admin@celeste7.ai)
4. **Password:** Email password OR App Password

### Security Note:
- If MFA enabled, must use "App Password" (not regular password)
- Generate at: https://account.microsoft.com/security

### What I Need From You:
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=admin@celeste7.ai
SMTP_PASSWORD=your_password_or_app_password
SENDER_EMAIL=noreply@celeste7.ai
SENDER_NAME=Celeste7 Yacht Onboarding
```

---

## Option 3: SendGrid (Third-party)
**Best for:** Simple, reliable, no Azure setup needed

### Required Information:
1. **SendGrid Account** (free tier: 100 emails/day)
2. **API Key**

### How to Get These:
```
1. Sign up: https://sendgrid.com
2. Verify sender email
3. Create API key: Settings > API Keys > Create API Key
4. Copy API key
```

### What I Need From You:
```
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=noreply@celeste7.ai
SENDER_NAME=Celeste7 Yacht Onboarding
```

---

## Option 4: Gmail SMTP
**Best for:** If you use Gmail

### Required Information:
1. **Gmail address**
2. **App Password** (not regular password)

### How to Get App Password:
```
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. Select: Mail + Other (Custom name: "CelesteOS")
4. Copy 16-character password
```

### What I Need From You:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx (16-char app password)
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Celeste7 Yacht Onboarding
```

---

## My Recommendation

### Best: Microsoft Graph API (Option 1)
**Why:**
- Most professional (uses Azure AD)
- No password in config (uses OAuth tokens)
- Better security
- Supports celeste7.ai domain email

**Setup Time:** 15-20 minutes
**Code Changes:** 30 minutes

### Easiest: SendGrid (Option 3)
**Why:**
- No Azure setup needed
- 5-minute setup
- Free tier sufficient
- Very reliable

**Setup Time:** 5 minutes
**Code Changes:** 20 minutes

### Quick Test: SMTP (Option 2 or 4)
**Why:**
- Works immediately if you have Office 365 or Gmail
- No additional account signup

**Setup Time:** 2 minutes (if you have credentials)
**Code Changes:** 20 minutes

---

## What Happens After You Provide Details?

### I Will:
1. Add email library to requirements.txt
2. Create `core/email/sender.py` module
3. Update `workflows/onboarding/register.py` to actually send emails
4. Test with your credentials
5. Verify email delivery

### Estimated Time:
- **Code changes:** 30-45 minutes
- **Testing:** 15 minutes
- **Total:** ~1 hour

---

## Current Email Code (Mock)

**File:** `workflows/onboarding/register.py`
```python
# Step 6: Send email
# TODO: Implement email sending via Microsoft Outlook API or SMTP
# For now, we'll simulate success
print(f"[EMAIL] Would send to {buyer_email}:")
print(f"[EMAIL] Subject: {email_data['subject']}")
print(f"[EMAIL] Activation Link: {email_data['activation_link']}")
```

**What it will become:**
```python
# Step 6: Send email
from core.email.sender import send_activation_email

try:
    send_activation_email(
        to=buyer_email,
        subject=email_data['subject'],
        html=email_data['html'],
        text=email_data['text']
    )
    print(f"[EMAIL] Sent to {buyer_email}")
except Exception as e:
    print(f"[EMAIL] Failed to send: {e}")
    # Still return success - don't fail registration if email fails
```

---

## Security Considerations

### DO NOT commit to git:
- ❌ SMTP passwords
- ❌ API keys
- ❌ Client secrets

### Store in .env file:
```bash
# .env (this file is in .gitignore)
SENDGRID_API_KEY=SG.xxxxx
SMTP_PASSWORD=xxxxx
AZURE_CLIENT_SECRET=xxxxx
```

### Already protected:
- ✅ `.env` is in `.gitignore`
- ✅ Credentials won't be committed
- ✅ Safe to add to `.env` file

---

## Testing Plan

Once you provide credentials:

1. **Test email sending:**
```python
python3 -c "
from core.email.sender import send_activation_email
send_activation_email(
    to='your-email@example.com',
    subject='Test Email',
    html='<h1>Test</h1>',
    text='Test'
)
print('✅ Email sent!')
"
```

2. **Test full workflow:**
```bash
python3 test_until_perfect.py
# Should send REAL emails this time
```

3. **Verify:**
- Check your inbox
- Click activation link
- Confirm it works

---

## What I Need From You (Summary)

### Pick ONE option and provide:

**Option 1 (Microsoft Graph API):**
```
AZURE_TENANT_ID=?
AZURE_CLIENT_ID=?
AZURE_CLIENT_SECRET=?
SENDER_EMAIL=?
```

**Option 2 (SMTP - Office 365):**
```
SMTP_USER=?
SMTP_PASSWORD=?
SENDER_EMAIL=?
```

**Option 3 (SendGrid):**
```
SENDGRID_API_KEY=?
SENDER_EMAIL=?
```

**Option 4 (Gmail SMTP):**
```
SMTP_USER=?
SMTP_PASSWORD=? (app password)
```

---

## Questions?

**Q: Which option should I use?**
A: If you have Office 365, use Microsoft Graph API (Option 1). Otherwise, use SendGrid (Option 3) - it's easiest.

**Q: How long will implementation take?**
A: 1 hour total (30 min code + 15 min testing + 15 min verification)

**Q: Will emails be reliable?**
A: Yes - all options are production-grade email services

**Q: What if I don't have any of these?**
A: I recommend signing up for SendGrid (free, 5 minutes) or I can help you set up Azure AD app registration

---

**Just tell me which option you want and provide the credentials, and I'll implement it immediately.**
