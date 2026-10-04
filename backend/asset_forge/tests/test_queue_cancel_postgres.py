"""Real transaction test against an ephemeral local CI Postgres database only."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest


def test_queue_reset_transaction_on_isolated_postgres():
    url = os.getenv("QUEUE_RESET_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("ephemeral Postgres is configured by backend CI")
    parsed = urlparse(url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path == "/queue_cancel_test"
    import psycopg

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                do $$ begin
                  create role service_role;
                exception when duplicate_object then null;
                end $$;
                do $$ begin
                  create role anon;
                exception when duplicate_object then null;
                end $$;
                do $$ begin
                  create role authenticated;
                exception when duplicate_object then null;
                end $$;
                create table public.content_jobs (
                  id uuid primary key, status text not null,
                  publish_status text not null default 'PENDING',
                  publora_post_id text, asset_ref text, telegram_ref text,
                  constraint content_jobs_status_check check (status in (
                    'NEW','READY_TO_PUBLISH','PUBLISHING','PUBLISHED'
                  ))
                );
                create table public.content_job_events (
                  id bigint generated always as identity primary key,
                  content_job_id uuid not null references public.content_jobs(id),
                  event_type text not null, from_status text, to_status text,
                  actor text not null, metadata jsonb not null default '{}'::jsonb
                );
            """)
            cur.execute(Path("supabase/migrations/202610040001_content_queue_cancel.sql").read_text())
            cur.execute("""
                insert into public.content_jobs (id,status,publora_post_id,asset_ref,telegram_ref)
                values
                  ('00000000-0000-4000-8000-000000000001','NEW',null,'asset-a','telegram-a'),
                  ('00000000-0000-4000-8000-000000000002','READY_TO_PUBLISH',null,'asset-b','telegram-b'),
                  ('00000000-0000-4000-8000-000000000003','PUBLISHING','draft-c','asset-c','telegram-c'),
                  ('00000000-0000-4000-8000-000000000004','PUBLISHED','post-d','asset-d','telegram-d')
            """)
            cur.execute("select public.cancel_content_jobs(null)")
            first = cur.fetchone()[0]
            assert (first["selected"], first["eligible"], first["cancelled"]) == (4, 2, 2)
            assert {r["reason"] for r in first["skipped"]} == {
                "TERMINAL", "EXTERNAL_RECONCILIATION_REQUIRED"
            }
            cur.execute("select public.cancel_content_jobs(null)")
            repeated = cur.fetchone()[0]
            assert repeated["cancelled"] == 0
            assert repeated["already_cancelled"] == 2
            cur.execute("select status,asset_ref,telegram_ref,publora_post_id from public.content_jobs order by id")
            rows = cur.fetchall()
            assert [r[0] for r in rows] == ["CANCELLED","CANCELLED","PUBLISHING","PUBLISHED"]
            assert [r[1] for r in rows] == ["asset-a","asset-b","asset-c","asset-d"]
            assert [r[2] for r in rows] == ["telegram-a","telegram-b","telegram-c","telegram-d"]
            assert rows[2][3] == "draft-c"
            cur.execute("select event_type,from_status,to_status from public.content_job_events order by id")
            events = cur.fetchall()
            assert len(events) == 2
            assert all(e[0] == "OWNER_CANCELLED" and e[2] == "CANCELLED" for e in events)
            cur.execute("select has_function_privilege('anon','public.cancel_content_jobs(uuid)','execute')")
            assert cur.fetchone()[0] is False
            cur.execute("select has_function_privilege('authenticated','public.cancel_content_jobs(uuid)','execute')")
            assert cur.fetchone()[0] is False
            cur.execute("select has_function_privilege('service_role','public.cancel_content_jobs(uuid)','execute')")
            assert cur.fetchone()[0] is True

        # The guard must prevent a worker, retry or Telegram handler from
        # changing an already-cancelled row, including non-status fields.
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("""
                    update public.content_jobs set status='READY_TO_PUBLISH'
                    where id='00000000-0000-4000-8000-000000000001'
                """)
