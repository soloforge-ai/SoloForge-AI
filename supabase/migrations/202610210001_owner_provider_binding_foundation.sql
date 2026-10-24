-- Inert persistence foundation. Not deployed; no spending authorization.
-- All writes are reserved for separately reviewed trusted service-role code.
CREATE TABLE IF NOT EXISTS public.owner_provider_bindings (
    owner_user_id uuid PRIMARY KEY,
    provider_account_id text NOT NULL CHECK (length(trim(provider_account_id)) > 0),
    internal_app_key_id text NOT NULL CHECK (length(trim(internal_app_key_id)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.owner_provider_key_rotations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_user_id uuid NOT NULL REFERENCES public.owner_provider_bindings(owner_user_id),
    provider_key_id text NOT NULL CHECK (length(trim(provider_key_id)) > 0),
    verified_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_user_id, provider_key_id)
);

ALTER TABLE public.owner_provider_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owner_provider_key_rotations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.owner_provider_bindings FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.owner_provider_key_rotations FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.owner_provider_key_rotations_id_seq FROM PUBLIC, anon, authenticated;
-- No SECURITY DEFINER RPC or API endpoint is created by this migration.
-- Immutable binding and atomic key rotation must be enforced by a reviewed
-- trusted service-role transaction before connecting this schema to runtime.
