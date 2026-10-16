# P0-B3 Remaining Foundation — Offline QA Contract

**Status:** fixture-only, advisory, no production integration.

The pure functions in `offline_qa_issuance.py` implement deterministic UTF-8 JSON canonicalization, HMAC-SHA256 test attestation, signature verification using a separately supplied trusted keyring, SHA256 verification of trusted in-memory artifact bytes, reviewer authorization via P0-B3.1, route-aware chain verification via P0-B2, read-only replay checks, and non-persistent audit record construction.

## Trusted fixture inputs

- Principal, grant, target, and evaluation time MUST originate from an authenticated future server authority, never from client-supplied QA envelopes.
- Signing key and verifier keyring are independent trusted fixture inputs. HMAC uses a **shared secret**, not a public-key signature. This code does not provide production key management, rotation, key provenance, or separation of signing and verification privileges.
- `trusted_snapshots`, `trusted_revision`, `route`, `trusted_artifacts`, and `consumed_evidence_ids` MUST be independently derived from authoritative immutable storage and a durable atomic ledger in any future production design. Current inputs are offline fixtures only.
- `trusted_artifacts` maps evidence ID to immutable **bytes**, not URLs. Output hashes are recomputed. Input hashes are syntax-checked and compared against trusted snapshots, but input artifact bytes are **not** independently retrieved or hashed.
- The replay ledger is read-only; the function cannot atomically reserve evidence IDs, prevent concurrent reuse, persist revocations, or write audit records.
- Attestation issuance checks reviewer authorization at issuance time. Verification checks signature and chain but **does not re-check current reviewer revocation or grant expiry**; future live acceptance must re-authorize against trusted current state.
- A caller that controls trusted fixtures or signing keys can forge an apparent PASS. A PASS is **never** sufficient for a production trust decision.

## Fail-closed invariants

P0-A `FINAL_QA` remains `BLOCKED/TRUSTED_STAGE_CHAIN_MISSING`; S1 generation and interactive-chat execution remain locked. No new API routes, DB migrations, OAuth, wallet, worker, publishing, provider, production configuration, or deployment changes. Runtime wiring, durable audit/replay/revocation, key management, trusted artifact retrieval, and production security authorization are expressly out of scope.
