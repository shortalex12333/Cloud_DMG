# CelesteOS Cloud

Cloud infrastructure for CelesteOS yacht management system.

## Supabase Project

- **Project ID:** `qvzmkaamzaqxpzbewjxe`
- **URL:** https://qvzmkaamzaqxpzbewjxe.supabase.co
- **Dashboard:** https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe

## Structure

```
CelesteOS-Cloud/
├── supabase/
│   └── migrations/
│       └── 001_complete_schema.sql   # Full database schema
├── portal/
│   └── supabase.ts                   # Next.js Supabase client
├── n8n-workflows/
│   ├── Signature_Installer_Cloud.json  # Yacht registration flow
│   ├── Portal_Cloud.json               # User login/2FA/download flow
│   └── ...
├── scripts/
├── docs/
├── .env                              # Local config (git ignored)
└── .env.example                      # Config template
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `fleet_registry` | Yacht identities + shared_secret |
| `user_accounts` | Portal user accounts |
| `user_sessions` | Active sessions |
| `twofa_codes` | 2FA verification codes |
| `download_links` | DMG download tokens |
| `audit_log` | Activity tracking |
| `security_events` | Security incidents |

## Setup

1. Copy `.env.example` to `.env`
2. Add `SUPABASE_SERVICE_ROLE_KEY` from Supabase Dashboard
3. Run migration in Supabase SQL Editor:
   ```
   supabase/migrations/001_complete_schema.sql
   ```

## n8n Workflows

### Signature_Installer_Cloud.json
- `POST /register` - Yacht registration
- `GET /activate/:yacht_id` - Email activation
- `POST /check-activation/:yacht_id` - Credential retrieval (ONE TIME)

### Portal_Cloud.json
- `POST /user-login` - Request 2FA code
- `POST /verify-2fa` - Verify code, get session
- `POST /download-request` - Request DMG download

## Security

- RLS enabled on all tables
- `shared_secret` only retrievable ONCE
- Sessions expire after 7 days
- 2FA codes expire after 10 minutes
- Download links expire after 7 days
