-- Add Aira TTS pipeline fields and statuses for SoloForge content jobs.

alter table public.content_jobs
    add column if not exists voice_profile text,
    add column if not exists audio_status text,
    add column if not exists audio_storage_path text,
    add column if not exists audio_generated_at timestamptz;

alter table public.content_jobs
    drop constraint if exists content_jobs_audio_status_check;

alter table public.content_jobs
    add constraint content_jobs_audio_status_check
    check (
        audio_status is null
        or audio_status in ('PENDING','GENERATING','READY','FAILED')
    );

alter table public.content_jobs
    drop constraint if exists content_jobs_status_check;

alter table public.content_jobs
    add constraint content_jobs_status_check
    check (status in (
        'NEW','SCORING','SCORED','SELECTED','BACKLOG','ARCHIVED',
        'GENERATING','READY_FOR_REVIEW','APPROVED',
        'AUDIO_GENERATING','AUDIO_READY','AUDIO_FAILED',
        'FINAL_RENDERING','RENDERING','READY_TO_PUBLISH',
        'PUBLISHING','PUBLISHED',
        'GENERATION_FAILED','RENDER_FAILED','PUBLISH_FAILED'
    ));

insert into storage.buckets (id, name, public)
values ('content-audio', 'content-audio', false)
on conflict (id) do nothing;
