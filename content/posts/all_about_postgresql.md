+++
date = '2026-01-16T08:54:28+11:00'
draft = false
title = 'PostgreSQL & TimescaleDB Essential Commands'
tags = ['postgresql', 'timescaledb', 'database', 'sql']
+++

A quick reference guide for common PostgreSQL and TimescaleDB operations here so I don't need to ask ChatGPT every time.

## Creating a New User

```sql
-- Create a new user with password
CREATE USER myuser WITH PASSWORD 'securepassword';

-- Create a user with specific attributes
CREATE USER myuser WITH 
  PASSWORD 'securepassword'
  LOGIN
  CREATEDB
  VALID UNTIL '2027-12-31';

-- Create a superuser (use with caution)
CREATE USER admin_user WITH PASSWORD 'adminpass' SUPERUSER;
```

## Granting User Permissions

### Database Level Permissions

```sql
-- Grant all privileges on a database
GRANT ALL PRIVILEGES ON DATABASE mydb TO myuser;

-- Grant connect privilege
GRANT CONNECT ON DATABASE mydb TO myuser;

-- Grant specific privileges
GRANT CREATE ON DATABASE mydb TO myuser;
```

### Schema Level Permissions

```sql
-- Grant all privileges on schema
GRANT ALL ON SCHEMA public TO myuser;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO myuser;

-- Grant create on schema
GRANT CREATE ON SCHEMA public TO myuser;
```

### Table Level Permissions

```sql
-- Grant all privileges on all tables in schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myuser;

-- Grant specific privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO myuser;

-- Grant on a specific table
GRANT SELECT, INSERT ON mytable TO myuser;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO myuser;
```

### Sequence Permissions

```sql
-- Grant usage on all sequences (needed for auto-increment columns)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO myuser;

-- Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO myuser;
```

### Function Permissions

```sql
-- Grant execute on all functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO myuser;

-- Set default privileges for future functions
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO myuser;
```

## TimescaleDB Scheduled Jobs

### Creating a Scheduled Job

```sql
-- Create a procedure to be scheduled
CREATE OR REPLACE PROCEDURE user_defined_action(job_id INT, config JSONB)
LANGUAGE PLPGSQL AS
$$
BEGIN
  RAISE NOTICE 'Executing action % with config %', job_id, config;
  -- Your custom logic here
END;
$$;

-- Schedule the job to run every hour
SELECT add_job('user_defined_action', '1h');

-- Schedule with flexible timing (next run = last finish + interval)
SELECT add_job('user_defined_action', '1h', fixed_schedule => false);
```

### Job with Specific Start Time

```sql
-- Run at midnight every Sunday
SELECT add_job(
  'user_defined_action',
  '1 week',
  initial_start => '2026-01-19 00:00:00+00'::timestamptz
);

-- Schedule with timezone for DST handling
SELECT add_job(
  'user_defined_action',
  '1 week',
  initial_start => '2026-01-19 00:00:00+00'::timestamptz,
  timezone => 'Australia/Melbourne'
);
```

### Job with Configuration

```sql
-- Create a job with custom configuration
SELECT add_job(
  'user_defined_action',
  '30 minutes',
  config => '{"retention_days": 90, "table_name": "metrics"}'::jsonb
);
```

### Managing Jobs

```sql
-- View all scheduled jobs
SELECT * FROM timescaledb_information.jobs;

-- Manually run a job
CALL run_job(1000);

-- Alter a job schedule
SELECT alter_job(1000, schedule_interval => '2h');

-- Disable a job
SELECT alter_job(1000, scheduled => false);

-- Enable a job
SELECT alter_job(1000, scheduled => true);

-- Delete a job
SELECT delete_job(1000);
```

### Practical Example: Data Retention Job

```sql
-- Create a procedure to delete old data
CREATE OR REPLACE PROCEDURE cleanup_old_data(job_id INT, config JSONB)
LANGUAGE PLPGSQL AS
$$
DECLARE
  retention_days INT;
BEGIN
  retention_days := (config->>'retention_days')::INT;
  
  DELETE FROM metrics
  WHERE time < NOW() - INTERVAL '1 day' * retention_days;
  
  RAISE NOTICE 'Cleaned up data older than % days', retention_days;
END;
$$;

-- Schedule cleanup to run daily at 2 AM
SELECT add_job(
  'cleanup_old_data',
  '1 day',
  initial_start => '2026-01-17 02:00:00+11'::timestamptz,
  config => '{"retention_days": 90}'::jsonb,
  timezone => 'Australia/Melbourne'
);
```

## Common Permission Check Queries

```sql
-- Check user privileges on database
SELECT datname, grantee, privilege_type
FROM information_schema.database_privileges
WHERE grantee = 'myuser';

-- Check table privileges
SELECT table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'myuser';

-- List all users and their roles
SELECT usename, usesuper, usecreatedb, usecreaterole
FROM pg_user;

-- Check current user
SELECT current_user;
```

## References

- [PostgreSQL User Management](https://www.postgresql.org/docs/current/user-manag.html)
- [TimescaleDB Jobs Documentation](https://www.tigerdata.com/docs/api/latest/jobs-automation/add_job)
- [PostgreSQL GRANT Documentation](https://www.postgresql.org/docs/current/sql-grant.html)