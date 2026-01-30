-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema for LlamaIndex tables (optional, LlamaIndex will create its own tables)
CREATE SCHEMA IF NOT EXISTS public;

-- Activity log table for user monitoring
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    resource_path VARCHAR(500),
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_activity_log_username ON activity_log(username);
CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_log_activity_type ON activity_log(activity_type);

-- Login requests table for user access requests
CREATE TABLE IF NOT EXISTS login_requests (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    request_ip VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    assigned_username VARCHAR(255),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_login_requests_status ON login_requests(status);
CREATE INDEX IF NOT EXISTS idx_login_requests_created_at ON login_requests(created_at);

-- Grant permissions
GRANT ALL ON SCHEMA public TO raguser;
