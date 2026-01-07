-- Table Aliases for n8n Workflow Compatibility
--
-- The n8n workflows reference tables by different names than what exists
-- in the current Supabase project. This migration creates VIEW aliases
-- to allow workflows to function without modification.
--
-- IMPORTANT: This is a temporary fix. The proper solution is to update
-- the n8n workflows to reference the correct table names.

-- Drop existing views if they exist
DROP VIEW IF EXISTS documents CASCADE;
DROP VIEW IF EXISTS document_chunks CASCADE;
DROP VIEW IF EXISTS graph_nodes CASCADE;
DROP VIEW IF EXISTS graph_edges CASCADE;
DROP VIEW IF EXISTS maintenance_facts CASCADE;

-- Create view aliases
CREATE OR REPLACE VIEW documents AS
SELECT * FROM doc_metadata;

CREATE OR REPLACE VIEW document_chunks AS
SELECT * FROM search_document_chunks;

CREATE OR REPLACE VIEW graph_nodes AS
SELECT * FROM search_graph_nodes;

CREATE OR REPLACE VIEW graph_edges AS
SELECT * FROM search_graph_edges;

CREATE OR REPLACE VIEW maintenance_facts AS
SELECT * FROM search_maintenance_facts;

-- Grant permissions
GRANT ALL ON documents TO authenticated;
GRANT ALL ON documents TO service_role;
GRANT ALL ON documents TO anon;

GRANT ALL ON document_chunks TO authenticated;
GRANT ALL ON document_chunks TO service_role;
GRANT ALL ON document_chunks TO anon;

GRANT ALL ON graph_nodes TO authenticated;
GRANT ALL ON graph_nodes TO service_role;
GRANT ALL ON graph_nodes TO anon;

GRANT ALL ON graph_edges TO authenticated;
GRANT ALL ON graph_edges TO service_role;
GRANT ALL ON graph_edges TO anon;

GRANT ALL ON maintenance_facts TO authenticated;
GRANT ALL ON maintenance_facts TO service_role;
GRANT ALL ON maintenance_facts TO anon;

-- Add comments for documentation
COMMENT ON VIEW documents IS 'Alias for doc_metadata table. Used by n8n workflows. Consider updating workflows to use doc_metadata directly.';
COMMENT ON VIEW document_chunks IS 'Alias for search_document_chunks table. Used by n8n workflows. Consider updating workflows to use search_document_chunks directly.';
COMMENT ON VIEW graph_nodes IS 'Alias for search_graph_nodes table. Used by n8n Graph RAG workflow.';
COMMENT ON VIEW graph_edges IS 'Alias for search_graph_edges table. Used by n8n Graph RAG workflow.';
COMMENT ON VIEW maintenance_facts IS 'Alias for search_maintenance_facts table. Used by n8n Graph RAG workflow.';
