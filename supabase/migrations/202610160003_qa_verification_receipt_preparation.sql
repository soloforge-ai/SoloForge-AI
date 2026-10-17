-- P0-B4 receipt/claim transaction preparation. DISPOSABLE CI ONLY.
-- No GRANT EXECUTE. No production migration or authorization.
-- A receipt row is NOT proof of cryptographic verification; a future trusted
-- issuer must authenticate, verify exact bytes and provision receipt atomically.
create table public.qa_verification_receipts (
 receipt_id uuid primary key,
 chain_claim_id uuid not null unique,
 job_id text not null,
 revision_id text not null,
 route text not null check (route in ('IMAGE','VIDEO')),
 evidence_ids text[] not null,
 artifact_digest text not null check (artifact_digest ~ '^[a-f0-9]{64}$'),
 issuer_id text not null,
 issued_at timestamptz not null,
 expires_at timestamptz not null,
 revoked_at timestamptz,
 consumed_at timestamptz,
 check (expires_at > issued_at)
);
alter table public.qa_verification_receipts enable row level security;
revoke all on public.qa_verification_receipts from public,anon,authenticated,service_role;

create function public.qa_claim_chain_with_receipt(
 p_receipt_id uuid, p_chain_claim_id uuid, p_job_id text,
 p_revision_id text, p_route text, p_evidence_ids text[],
 p_artifact_digest text
) returns boolean language plpgsql security definer set search_path = ''
as $$
declare r public.qa_verification_receipts%rowtype;
begin
 if p_receipt_id is null or p_chain_claim_id is null
    or p_artifact_digest is null or p_evidence_ids is null then return false; end if;
 select * into r from public.qa_verification_receipts
   where receipt_id=p_receipt_id for update;
 if not found or r.consumed_at is not null or r.revoked_at is not null
    or r.issued_at > clock_timestamp() or r.expires_at <= clock_timestamp()
    or r.chain_claim_id <> p_chain_claim_id or r.job_id <> p_job_id
    or r.revision_id <> p_revision_id or r.route <> p_route
    or r.evidence_ids <> p_evidence_ids
    or r.artifact_digest <> p_artifact_digest then return false; end if;
 -- Locks receipt before claim; PostgreSQL rollback includes all writes.
 -- Underlying chain RPC locks grants and checks replay/order in same transaction.
 if public.qa_claim_verified_chain(p_chain_claim_id,p_job_id,p_revision_id,
                                    p_route,p_evidence_ids) is not true then
   return false;
 end if;
 update public.qa_verification_receipts set consumed_at=clock_timestamp()
   where receipt_id=p_receipt_id and consumed_at is null;
 return found;
end $$;
revoke all on function public.qa_claim_chain_with_receipt(uuid,uuid,text,text,text,text[],text)
 from public,anon,authenticated,service_role;
-- Critical limitation: PostgreSQL owner can seed receipts in CI. This function
-- MUST NOT be granted to any live role until DB-bound cryptographic provenance,
-- immutable artifact version/hash locking and issuer authorization are proven.
