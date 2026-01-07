# Future Workflows

These workflows are planned but not yet deployed.

## Portal_Cloud.json
User-facing portal for yacht buyers.

**Endpoints:**
- `POST /user-login` - User portal login
- `POST /verify-2fa` - 2FA verification  
- `POST /download-request` - DMG download request

**Status:** Awaiting user portal frontend

**Database:** `user_accounts`, `user_sessions` tables exist but unused

**When to Deploy:**
When user portal UI is built and ready for production.
