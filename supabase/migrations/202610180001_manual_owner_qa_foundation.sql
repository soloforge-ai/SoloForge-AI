-- Manual owner QA foundation only. No live execution, no worker enablement.
-- A trusted server must independently verify owner/wallet binding and provider limits
-- BEFORE provisioning an allocation. No client can create or spend allocations.
create table if not exists public.manual_qa_allocations (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null,
 wallet_binding_ref text not null check (length(wallet_binding_ref) between 8 and 256),
 provider_model text not null check (length(provider_model) between 3 and 160),
 authorized_budget numeric(18,8) not null check (authorized_budget > 0),
 reserved_budget numeric(18,8) not null default 0 check (reserved_budget >= 0),
 consumed_budget numeric(18,8) not null default 0 check (consumed_budget >= 0),
 expires_at timestamptz not null,
 revoked_at timestamptz,
 created_at timestamptz not null default now(),
 constraint manual_qa_allocation_budget_check check (reserved_budget + consumed_budget <= authorized_budget)
);
create table if not exists public.manual_qa_requests (
 id uuid primary key default gen_random_uuid(),
 allocation_id uuid not null references public.manual_qa_allocations(id),
 idempotency_key text not null unique check (length(idempotency_key) between 16 and 128),
 request_sha256 text not null check (request_sha256 ~ '^[0-9a-f]{64}$'),
 model text not null,
 reserved_cost numeric(18,8) not null check (reserved_cost > 0),
 actual_cost numeric(18,8),
 status text not null default 'CALL_STARTED'
   check (status in ('CALL_STARTED','SUCCEEDED','RECONCILIATION_REQUIRED')),
 created_at timestamptz not null default now(),
 settled_at timestamptz,
 constraint manual_qa_actual_cost_check check (actual_cost is null or (actual_cost >= 0 and actual_cost <= reserved_cost))
);
create index if not exists manual_qa_requests_allocation_idx on public.manual_qa_requests(allocation_id);
alter table public.manual_qa_allocations enable row level security;
alter table public.manual_qa_requests enable row level security;
revoke all on public.manual_qa_allocations, public.manual_qa_requests from public, anon, authenticated;
revoke all on public.manual_qa_allocations, public.manual_qa_requests from service_role;
grant select on public.manual_qa_allocations, public.manual_qa_requests to service_role;
-- Only a trusted server may call these RPCs; service_role possession alone is
-- not proof of wallet ownership. Never expose service_role to Flutter.
create or replace function public.manual_qa_claim(
 p_allocation_id uuid, p_idempotency_key text, p_request_sha256 text,
 p_model text, p_reserved_cost numeric
) returns table(request_id uuid, should_dispatch boolean, request_status text)
language plpgsql security definer set search_path = ''
as $$
declare a public.manual_qa_allocations%rowtype;
        prior public.manual_qa_requests%rowtype;
        new_id uuid;
begin
 if auth.role() is distinct from 'service_role' then
   raise exception 'service role required' using errcode='42501';
 end if;
 if p_idempotency_key is null or length(p_idempotency_key) not between 16 and 128
    or p_request_sha256 is null or p_request_sha256 !~ '^[0-9a-f]{64}$'
    or p_reserved_cost is null or p_reserved_cost <= 0 then
   raise exception 'invalid manual QA claim';
 end if;
 -- Serialize every claim against this allocation, including distinct request keys.
 select * into a from public.manual_qa_allocations
 where id=p_allocation_id for update;
 if not found then raise exception 'allocation unavailable'; end if;
 select * into prior from public.manual_qa_requests where idempotency_key=p_idempotency_key;
 if found then
   if prior.allocation_id <> p_allocation_id
      or prior.request_sha256 <> p_request_sha256
      or prior.model <> p_model or prior.reserved_cost <> p_reserved_cost then
     raise exception 'idempotency key conflict';
   end if;
   return query select prior.id, false, prior.status;
   return;
 end if;
 if a.revoked_at is not null or a.expires_at <= now()
    or a.provider_model <> p_model
    or a.authorized_budget - a.consumed_budget - a.reserved_budget < p_reserved_cost then
   raise exception 'manual QA allocation blocked';
 end if;
 update public.manual_qa_allocations set reserved_budget=reserved_budget+p_reserved_cost
 where id=a.id;
 insert into public.manual_qa_requests(allocation_id,idempotency_key,request_sha256,model,reserved_cost)
 values (a.id,p_idempotency_key,p_request_sha256,p_model,p_reserved_cost)
 returning id into new_id;
 return query select new_id,true,'CALL_STARTED'::text;
end $$;
create or replace function public.manual_qa_settle(
 p_request_id uuid, p_outcome text, p_actual_cost numeric default null
) returns text
language plpgsql security definer set search_path = ''
as $$
declare r public.manual_qa_requests%rowtype;
begin
 if auth.role() is distinct from 'service_role' then
   raise exception 'service role required' using errcode='42501';
 end if;
 select * into r from public.manual_qa_requests where id=p_request_id for update;
 if not found then raise exception 'request unavailable'; end if;
 if r.status <> 'CALL_STARTED' then
   raise exception 'already finalized; reconciliation required';
 end if;
 if p_outcome = 'SUCCEEDED' and p_actual_cost is not null
    and p_actual_cost >= 0 and p_actual_cost <= r.reserved_cost then
   update public.manual_qa_allocations
     set reserved_budget=reserved_budget-r.reserved_cost,
         consumed_budget=consumed_budget+p_actual_cost
     where id=r.allocation_id;
   update public.manual_qa_requests set status='SUCCEEDED',
     actual_cost=p_actual_cost,settled_at=now() where id=r.id;
   return 'SUCCEEDED';
 end if;
 -- Never release reservation for an ambiguous provider result or unknown cost.
 if p_outcome <> 'RECONCILIATION_REQUIRED' then
   raise exception 'invalid or unverified settlement; reconcile first';
 end if;
 update public.manual_qa_requests set status='RECONCILIATION_REQUIRED',
   settled_at=now() where id=r.id;
 return 'RECONCILIATION_REQUIRED';
end $$;
revoke all on function public.manual_qa_claim(uuid,text,text,text,numeric) from public,anon,authenticated;
revoke all on function public.manual_qa_settle(uuid,text,numeric) from public,anon,authenticated;
grant execute on function public.manual_qa_claim(uuid,text,text,text,numeric) to service_role;
grant execute on function public.manual_qa_settle(uuid,text,numeric) to service_role;
