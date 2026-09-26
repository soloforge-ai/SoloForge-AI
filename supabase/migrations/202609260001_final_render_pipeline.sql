-- Final render pipeline fields for SoloForge content jobs.

alter table public.content_jobs
    add column if not exists render_status text,
    add column if not exists video_storage_path text,
    add column if not exists render_mode text,
    add column if not exists render_generated_at timestamptz,
    add column if not exists render_qa jsonb;

alter table public.content_jobs
    drop constraint if exists content_jobs_render_status_check;

alter table public.content_jobs
    add constraint content_jobs_render_status_check
    check (
        render_status is null
        or render_status in ('PENDING','RENDERING','READY','FAILED','BLOCKED_NO_VIDEO')
    );

insert into storage.buckets (id, name, public)
values ('content-video', 'content-video', false)
on conflict (id) do nothing;
