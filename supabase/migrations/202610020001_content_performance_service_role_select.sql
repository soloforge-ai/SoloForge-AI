-- Phase 2 worker prerequisite:
-- content generation reads performance feedback through the service-role REST client.
-- Keep this grant in migration history so new environments reproduce production.

grant select on table public.content_performance_snapshots to service_role;
