#!/bin/bash
# Apply activation token migration to Supabase

echo "Applying 002_activation_tokens.sql migration..."
echo "================================================================"

# Read the SQL file and execute via Supabase REST API
SQL_CONTENT=$(cat ../supabase/migrations/002_activation_tokens.sql)

# Use jq to properly escape the SQL for JSON
SQL_JSON=$(jq -n --arg sql "$SQL_CONTENT" '{query: $sql}')

# Execute via Supabase REST API
curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/rpc/exec" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q" \
  -H "Content-Type: application/json" \
  -d "$SQL_JSON"

echo
echo "================================================================"
echo "Migration complete! Please verify functions in Supabase Dashboard."
echo
echo "Test with:"
echo "  SELECT * FROM generate_activation_token('TEST_YACHT_003', 24);"
