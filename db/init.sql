-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema for LlamaIndex tables (optional, LlamaIndex will create its own tables)
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO raguser;
