-- PostgreSQL initialization script
-- Runs once when the container is first created

-- Create the codebattle database (already created by POSTGRES_DB env var)
-- This file is for any additional setup

-- Enable UUID extension (useful for future UUID primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Grant full privileges to the app user
GRANT ALL PRIVILEGES ON DATABASE codebattle_db TO codebattle;

SELECT 'CodeBattle database initialized successfully!' AS status;
