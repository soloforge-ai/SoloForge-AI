# Data Model V0

Suggested PostgreSQL/Supabase entities.

## profiles
- id uuid pk
- name text
- niche text
- audience text
- created_at timestamptz

## affiliate_programs
- id uuid pk
- external_id text
- name text
- website text
- category text
- description text
- commission_type text
- commission_value numeric
- cookie_days integer
- recurring boolean
- pricing text
- free_trial boolean
- application_url text
- source text
- source_url text
- verified_at timestamptz
- created_at timestamptz
- updated_at timestamptz

## user_programs
- id uuid pk
- profile_id uuid fk
- program_id uuid fk
- status text
- affiliate_url text
- joined_at timestamptz
- notes text
- created_at timestamptz
- updated_at timestamptz

## opportunity_scores
- id uuid pk
- profile_id uuid fk
- program_id uuid fk
- audience_fit numeric
- content_potential numeric
- commission_score numeric
- product_value numeric
- competition numeric
- total_score numeric
- rationale jsonb
- created_at timestamptz

## content_items
- id uuid pk
- profile_id uuid fk
- program_id uuid fk
- title text
- platform text
- format text
- intent text
- goal text
- status text
- hook jsonb
- script text
- shot_list jsonb
- voiceover text
- visual_prompts jsonb
- cta text
- description text
- affiliate_disclosure text
- evidence_status text
- created_at timestamptz
- updated_at timestamptz

## content_claims
- id uuid pk
- content_id uuid fk
- claim_text text
- claim_type text
- evidence_required text
- evidence jsonb
- verification_status text

## content_tools
- id uuid pk
- content_id uuid fk
- tool_name text
- role text
- affiliate_url text
- used_in_final_output boolean default true

## tracking_links
- id uuid pk
- program_id uuid fk
- content_id uuid fk
- slug text unique
- target_url text
- active boolean default true
- created_at timestamptz

## click_events
- id bigint generated always as identity pk
- tracking_link_id uuid fk
- occurred_at timestamptz
- referrer text
- user_agent_hash text nullable

## performance_entries
- id uuid pk
- program_id uuid fk
- content_id uuid fk nullable
- conversions integer default 0
- revenue numeric default 0
- currency text default 'THB'
- period_start date
- period_end date
- source text
- created_at timestamptz

## Derived metrics

clicks = count(click_events)
conversion_rate = conversions / clicks
EPC = revenue / clicks

## Security baseline

- Row-level security for user-owned records.
- Never expose service-role keys to the client.
- Tracking redirects use server-side handlers.
- Do not store raw sensitive personal identifiers from visitors.
