-- Migration: Create yacht_documents table with pgvector for embeddings
-- Date: 2025-11-26
-- Purpose: Store document chunks with text embeddings generated in cloud

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create yacht_documents table
CREATE TABLE IF NOT EXISTS yacht_documents (
    id BIGSERIAL PRIMARY KEY,

    -- Yacht identification
    yacht_id TEXT NOT NULL,

    -- File identification
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,

    -- Chunk data
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    char_start INTEGER,
    char_end INTEGER,

    -- Document metadata
    section TEXT,
    page_numbers INTEGER[],
    metadata JSONB DEFAULT '{}',

    -- Embeddings (generated in cloud with text-embedding-3-small)
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one chunk per file per index
    UNIQUE(yacht_id, file_hash, chunk_index)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_yacht_documents_yacht_id
    ON yacht_documents(yacht_id);

CREATE INDEX IF NOT EXISTS idx_yacht_documents_file_hash
    ON yacht_documents(file_hash);

CREATE INDEX IF NOT EXISTS idx_yacht_documents_created_at
    ON yacht_documents(created_at DESC);

-- Vector similarity index (HNSW for fast approximate search)
CREATE INDEX IF NOT EXISTS idx_yacht_documents_embedding
    ON yacht_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Enable Row Level Security
ALTER TABLE yacht_documents ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Yachts can only see their own documents
CREATE POLICY yacht_documents_isolation ON yacht_documents
    FOR ALL
    USING (yacht_id = current_setting('request.jwt.claims', true)::json->>'yacht_id');

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON yacht_documents TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON yacht_documents TO service_role;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_yacht_documents_updated_at
    BEFORE UPDATE ON yacht_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Helper function: Search documents by similarity
CREATE OR REPLACE FUNCTION search_yacht_documents(
    p_yacht_id TEXT,
    p_query_embedding vector(1536),
    p_limit INTEGER DEFAULT 10,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id BIGINT,
    file_path TEXT,
    chunk_text TEXT,
    section TEXT,
    page_numbers INTEGER[],
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        yd.id,
        yd.file_path,
        yd.chunk_text,
        yd.section,
        yd.page_numbers,
        1 - (yd.embedding <=> p_query_embedding) AS similarity,
        yd.metadata
    FROM yacht_documents yd
    WHERE yd.yacht_id = p_yacht_id
      AND yd.embedding IS NOT NULL
      AND (1 - (yd.embedding <=> p_query_embedding)) >= p_similarity_threshold
    ORDER BY yd.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on search function
GRANT EXECUTE ON FUNCTION search_yacht_documents TO authenticated;
GRANT EXECUTE ON FUNCTION search_yacht_documents TO service_role;

COMMENT ON TABLE yacht_documents IS 'Stores document chunks with embeddings for semantic search';
COMMENT ON COLUMN yacht_documents.embedding IS 'Vector embedding from OpenAI text-embedding-3-small (1536 dimensions)';
COMMENT ON FUNCTION search_yacht_documents IS 'Semantic search across yacht documents using cosine similarity';
