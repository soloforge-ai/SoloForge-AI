-- Owner Queue Reset contract. Apply only after Batch A backend/API deployment is ready.
-- Existing rows are preserved. The backend is the sole caller (service_role), after
-- validating the owner-bound SoloForge session. This migration is not applied by CI.

alter table public.content_jobs drop constraint content_jobs_status_check;
alter table public.content_jobs add constraint content_jobs_status_check
check (status in (
  'NEW', 'SCORING', 'SCORED', 'SELECTED', 'BACKLOG', 'ARCHIVED',
  'GENERATING', 'READY_FOR_REVIEW', 'APPROVED', 'ASSET_QUEUED',
  'ASSET_GENERATING', 'ASSET_READY', 'ASSET_FAILED', 'AUDIO_GENERATING',
  'AUDIO_READY', 'AUDIO_FAILED', 'FINAL_RENDERING', 'RENDERING',
  'READY_TO_PUBLISH', 'PUBLISHING', 'PUBLISHED', 'GENERATION_FAILED',
  'RENDER_FAILED', 'PUBLISH_FAILED', 'CANCELLED'
));

create or replace function public.guard_cancelled_content_job()
returns trigger language plpgsql set search_path = public as $$
begin
  if old.status = 'CANCELLED' then
    raise exception 'CANCELLED content job is immutable' using errcode = '23514';
  end if;
  if new.status = 'CANCELLED' and (
    old.status not in (
      'NEW', 'SCORED', 'SELECTED', 'BACKLOG', 'READY_FOR_REVIEW',
      'APPROVED', 'ASSET_QUEUED', 'ASSET_READY', 'AUDIO_READY',
      'READY_TO_PUBLISH'
    )
    or old.publora_post_id is not null
    or (old.status = 'READY_TO_PUBLISH' and old.publish_status <> 'PENDING')
  ) then
    raise exception 'Job cannot be safely cancelled in current state'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger a_content_jobs_cancelled_guard
before update on public.content_jobs
for each row execute function public.guard_cancelled_content_job();

-- NULL job ID selects the whole queue. All decisions and writes occur in one
-- database transaction, with row locks serialized against worker claims.
create or replace function public.cancel_content_jobs(p_job_id uuid default null)
returns jsonb language plpgsql security invoker set search_path = public as $$
declare
  job record;
  selected_count integer := 0;
  eligible_count integer := 0;
  cancelled_count integer := 0;
  already_count integer := 0;
  changed jsonb := '[]'::jsonb;
  skipped jsonb := '[]'::jsonb;
  reason text;
begin
  perform set_config('lock_timeout', '5s', true);
  for job in
    select id, status, publish_status, publora_post_id
      from public.content_jobs
     where p_job_id is null or id = p_job_id
     order by id for update
  loop
    selected_count := selected_count + 1;
    if job.status = 'CANCELLED' then
      already_count := already_count + 1;
      continue;
    end if;
    reason := null;
    if job.status = 'PUBLISHING' or job.publora_post_id is not null then
      reason := 'EXTERNAL_RECONCILIATION_REQUIRED';
    elsif job.status in (
      'ARCHIVED', 'PUBLISHED', 'GENERATION_FAILED', 'ASSET_FAILED',
      'AUDIO_FAILED', 'RENDER_FAILED', 'PUBLISH_FAILED'
    ) then
      reason := 'TERMINAL';
    elsif job.status in (
      'SCORING', 'GENERATING', 'ASSET_GENERATING', 'AUDIO_GENERATING',
      'FINAL_RENDERING', 'RENDERING'
    ) then
      reason := 'IN_FLIGHT';
    elsif job.status = 'READY_TO_PUBLISH' and job.publish_status <> 'PENDING' then
      reason := 'EXTERNAL_RECONCILIATION_REQUIRED';
    elsif job.status not in (
      'NEW', 'SCORED', 'SELECTED', 'BACKLOG', 'READY_FOR_REVIEW',
      'APPROVED', 'ASSET_QUEUED', 'ASSET_READY', 'AUDIO_READY',
      'READY_TO_PUBLISH'
    ) then
      reason := 'UNSUPPORTED_STATE';
    end if;
    if reason is not null then
      skipped := skipped || jsonb_build_array(jsonb_build_object(
        'id', job.id, 'status', job.status, 'reason', reason,
        'publora_post_id', job.publora_post_id
      ));
      continue;
    end if;

    eligible_count := eligible_count + 1;
    update public.content_jobs set status = 'CANCELLED' where id = job.id;
    insert into public.content_job_events (
      content_job_id, event_type, from_status, to_status, actor, metadata
    ) values (
      job.id, 'OWNER_CANCELLED', job.status, 'CANCELLED',
      'soloforge_owner', jsonb_build_object(
        'scope', case when p_job_id is null then 'queue_reset' else 'single_job' end
      )
    );
    cancelled_count := cancelled_count + 1;
    changed := changed || jsonb_build_array(job.id);
  end loop;
  return jsonb_build_object(
    'selected', selected_count, 'eligible', eligible_count,
    'cancelled', cancelled_count, 'already_cancelled', already_count,
    'cancelled_ids', changed, 'skipped', skipped
  );
end;
$$;

revoke all on function public.cancel_content_jobs(uuid) from public, anon, authenticated;
grant execute on function public.cancel_content_jobs(uuid) to service_role;
revoke all on function public.guard_cancelled_content_job() from public, anon, authenticated;
