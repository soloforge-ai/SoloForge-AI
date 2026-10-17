-- P2-B1 disposable PostgreSQL-only prerequisite fixture.
-- Synthetic schema only: never use this file in Supabase production.
create extension if not exists pgcrypto;
do $$
begin
 if not exists(select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
 if not exists(select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
 if not exists(select 1 from pg_roles where rolname='service_role') then create role service_role nologin bypassrls; end if;
end $$;
create schema if not exists auth;
create table if not exists auth.users(id uuid primary key);
create table if not exists public.content_jobs(id uuid primary key);
create table if not exists public.pollinations_sessions(session_id text primary key);
-- The Phase 1 SQL references auth.users and public.content_jobs.
-- The fixture deliberately does not create trusted wallet verification evidence.
-- Test cases must seed explicit synthetic records; never import production data.
