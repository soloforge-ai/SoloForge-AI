# P2-B1 Trusted Provider Attestation Contract — fail closed

Status: **NO LIVE ISSUER / NO MERGE / NO PROVIDER EXECUTION**.

## Trust boundary
A Supabase OAuth session, user ID, service-role credential, public wallet statistics, or database timestamp **does not prove** ownership of a Pollinations wallet or authority to spend its funds. A caller-provided `evidence_ref`, `p_actual`, or `provider_wallet_fingerprint` is not verification.

Only a separately authenticated, independently authorized provider-verification authority may issue a wallet attestation. The application service role and user JWTs must not mint, amend, or revoke these records. CI's postgres superuser seeding is synthetic test setup **only** and must never be used as a production issuer.

## Required issuer evidence (not implemented)
- Provider-confirmed subject and OAuth session binding to the requesting `auth.users.id`; authenticated provider response provenance.
- Wallet identity/fingerprint, category (QUEST/PAID), ownership and explicit spending permission, independently verified (not public stats).
- Dedicated allocation ID, authorized amount, currency/unit, authorization scope and expiry; no app-key fallback.
- Immutable evidence digest, issuer identity, source/request correlation, issued/verified time, revocation and replay protection.
- Cryptographic or provider-backed verification of all evidence **before** issuance, and periodic revocation/expiry checks before new spending.

## Database gate
`generation_trust.wallet_attestations` is private and denied to `service_role`. `generation_trust.check_wallet` checks bound owner, session, wallet fingerprint, category, allocation, expiry and revocation. It is **not** a provider verifier. Without an attestation issued by an independently trusted authority, reservations fail closed. A future issuer needs a separate security review and dedicated migration, not an application RPC that accepts asserted values.

## Settlement and recovery
The current `generation_record_verified_result`, `generation_settle_execution` and `generation_resume_after_reconciliation` still accept caller-supplied provider evidence. Their synthetic tests do not prove trusted provider verification. Do not enable external execution or release real wallet reservations until provider-result verification and evidence-bound settlement are implemented and independently tested.

## Release gate
Security approval requires verified effective role privileges on a production-equivalent Supabase role model, provider-issued attestation provenance, provider-result evidence verification, reconciliation fail-closed tests, and full PostgreSQL CI. A green CI run alone is insufficient.
