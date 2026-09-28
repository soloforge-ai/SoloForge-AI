-- Sprint 3: route approved content through text, visual, or video production.

alter table public.content_jobs
    drop constraint if exists content_jobs_status_check;

alter table public.content_jobs
    add constraint content_jobs_status_check
    check (status in (
        'NEW','SCORING','SCORED','SELECTED','BACKLOG','ARCHIVED',
        'GENERATING','READY_FOR_REVIEW','APPROVED',
        'ASSET_QUEUED','ASSET_GENERATING','ASSET_READY','ASSET_FAILED',
        'AUDIO_GENERATING','AUDIO_READY','AUDIO_FAILED',
        'FINAL_RENDERING','RENDERING','READY_TO_PUBLISH',
        'PUBLISHING','PUBLISHED',
        'GENERATION_FAILED','RENDER_FAILED','PUBLISH_FAILED'
    ));

insert into storage.buckets (id, name, public)
values ('content-assets', 'content-assets', false)
on conflict (id) do nothing;
