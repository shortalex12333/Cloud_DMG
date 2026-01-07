// Edge Function: Delete Document Chunks
// Removes all chunks for a file when it's deleted from the yacht

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { createHmac } from 'https://deno.land/std@0.168.0/node/crypto.ts';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

interface DeleteRequest {
  yacht_id: string;
  file_hash: string;
}

// Verify HMAC signature
function verifySignature(
  payload: DeleteRequest,
  timestamp: string,
  signature: string,
  yachtIdHash: string
): boolean {
  try {
    const message = JSON.stringify(payload) + timestamp;
    const expectedSignature = createHmac('sha256', yachtIdHash)
      .update(message)
      .digest('hex');

    return signature === expectedSignature;
  } catch (error) {
    console.error('Signature verification error:', error);
    return false;
  }
}

serve(async (req: Request) => {
  // CORS headers
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type, X-Yacht-ID, X-Timestamp, X-Signature',
      },
    });
  }

  try {
    // Validate request method
    if (req.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Get headers
    const yachtId = req.headers.get('X-Yacht-ID');
    const timestamp = req.headers.get('X-Timestamp');
    const signature = req.headers.get('X-Signature');

    if (!yachtId || !timestamp || !signature) {
      return new Response(JSON.stringify({ error: 'Missing authentication headers' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Parse body
    const payload: DeleteRequest = await req.json();

    // Validate payload
    if (!payload.file_hash) {
      return new Response(JSON.stringify({ error: 'Invalid payload: file_hash required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (payload.yacht_id !== yachtId) {
      return new Response(JSON.stringify({ error: 'Yacht ID mismatch' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check timestamp (prevent replay attacks)
    const requestTime = parseInt(timestamp);
    const now = Math.floor(Date.now() / 1000);
    const maxAge = 300; // 5 minutes

    if (Math.abs(now - requestTime) > maxAge) {
      return new Response(JSON.stringify({ error: 'Request timestamp too old or in future' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Get yacht from database
    const supabase = createClient(SUPABASE_URL!, SUPABASE_SERVICE_ROLE_KEY!);

    const { data: yacht, error: yachtError } = await supabase
      .from('fleet_registry')
      .select('yacht_id, yacht_id_hash')
      .eq('yacht_id', yachtId)
      .single();

    if (yachtError || !yacht) {
      return new Response(JSON.stringify({ error: 'Yacht not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Verify HMAC signature
    if (!verifySignature(payload, timestamp, signature, yacht.yacht_id_hash)) {
      return new Response(JSON.stringify({ error: 'Invalid signature' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Delete chunks
    console.log(`Deleting chunks for file hash ${payload.file_hash}, yacht ${yachtId}`);

    const { data, error } = await supabase
      .from('yacht_documents')
      .delete()
      .eq('yacht_id', yachtId)
      .eq('file_hash', payload.file_hash);

    if (error) {
      console.error('Delete error:', error);
      return new Response(JSON.stringify({
        error: 'Failed to delete chunks',
        message: error.message,
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Return success
    return new Response(JSON.stringify({
      success: true,
      file_hash: payload.file_hash,
      deleted: true,
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });

  } catch (error) {
    console.error('Delete error:', error);

    return new Response(JSON.stringify({
      error: 'Internal server error',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
