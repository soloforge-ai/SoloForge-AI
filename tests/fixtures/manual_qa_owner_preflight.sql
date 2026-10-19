-- Synthetic schema ONLY; GitHub-hosted disposable PostgreSQL 16.
CREATE TABLE auth.users (id uuid PRIMARY KEY);
INSERT INTO auth.users(id) VALUES ('72112ead-d399-4a40-aa51-ee17811cb10d');
CREATE TABLE public.pollinations_sessions (
 id uuid PRIMARY KEY,
 session_id text UNIQUE NOT NULL,
 access_token text NOT NULL,
 refresh_token text,
 token_type text DEFAULT 'Bearer',
 scope text,
 expires_at timestamptz,
 created_at timestamptz DEFAULT now(),
 updated_at timestamptz DEFAULT now()
);
INSERT INTO public.pollinations_sessions(id,session_id,access_token)
VALUES ('00000000-0000-0000-0000-000000000001','legacy','synthetic-only');
