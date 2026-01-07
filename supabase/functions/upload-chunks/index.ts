// Edge Function: Upload Document Chunks with Embeddings
// Receives text chunks from local agent, generates embeddings, stores in database

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { createHmac } from 'https://deno.land/std@0.168.0/node/crypto.ts';

const OPENAI_API_KEY = Deno.env.get('OPENAI_API_KEY');
const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

interface ChunkData {
  text: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  file_path: string;
  file_hash: string;
  metadata: Record<string, any>;
  section: string | null;
  page_numbers: number[];
}

interface UploadRequest {
  yacht_id: string;
  chunks: ChunkData[];
}

// Verify HMAC signature
function verifySignature(
  payload: UploadRequest,
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

// Generate embedding using OpenAI
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'text-embedding-3-small',
      input: text,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error: ${response.status} ${error}`);
  }

  const data = await response.json();
  return data.data[0].embedding;
}

// Process chunks in batches to avoid rate limits
async function processChunksBatch(
  chunks: ChunkData[],
  yachtId: string,
  supabase: any
): Promise<{ success: number; failed: number }> {
  let success = 0;
  let failed = 0;

  // Process chunks one at a time to respect rate limits
  // TODO: Optimize with batch embedding API when available
  for (const chunk of chunks) {
    try {
      console.log(`Processing chunk ${chunk.chunk_index} from ${chunk.file_path}`);

      // Generate embedding
      const embedding = await generateEmbedding(chunk.text);

      // Insert into database
      const { error } = await supabase
        .from('yacht_documents')
        .upsert({
          yacht_id: yachtId,
          file_path: chunk.file_path,
          file_hash: chunk.file_hash,
          chunk_index: chunk.chunk_index,
          chunk_text: chunk.text,
          char_start: chunk.char_start,
          char_end: chunk.char_end,
          section: chunk.section,
          page_numbers: chunk.page_numbers,
          metadata: chunk.metadata,
          embedding: embedding,
        }, {
          onConflict: 'yacht_id,file_hash,chunk_index'
        });

      if (error) {
        console.error(`Failed to insert chunk ${chunk.chunk_index}:`, error);
        failed++;
      } else {
        success++;
      }

      // Rate limiting: wait 100ms between requests
      await new Promise(resolve => setTimeout(resolve, 100));

    } catch (error) {
      console.error(`Error processing chunk ${chunk.chunk_index}:`, error);
      failed++;
    }
  }

  return { success, failed };
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
    const payload: UploadRequest = await req.json();

    // Validate payload
    if (!payload.chunks || !Array.isArray(payload.chunks)) {
      return new Response(JSON.stringify({ error: 'Invalid payload: chunks array required' }), {
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

    // Get yacht from database to verify and get yacht_id_hash
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

    // Process chunks
    console.log(`Processing ${payload.chunks.length} chunks for yacht ${yachtId}`);

    const result = await processChunksBatch(payload.chunks, yachtId, supabase);

    // Return response
    return new Response(JSON.stringify({
      success: true,
      processed: payload.chunks.length,
      uploaded: result.success,
      failed: result.failed,
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });

  } catch (error) {
    console.error('Upload error:', error);

    return new Response(JSON.stringify({
      error: 'Internal server error',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
