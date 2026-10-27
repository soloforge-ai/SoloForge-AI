"""Offline App Key contract preparation, not live attribution or spending authority.

Verified against pollinations/pollinations 5fe341f5690bb0c553c02ab77f35a9a762413fe3.
Existing manually submitted SKs have no evidenced byop_client_key_id here.
No provider I/O, credential creation, automatic redirect or earnings settlement.
"""
from urllib.parse import urlsplit
from .pollinations_oauth import (
    DEFAULT_AUTHORIZE_URL, DEFAULT_TOKEN_URL, build_authorization_url,
)

QUESTS_URL = "https://enter.pollinations.ai/quests"


def prepare_app_authorization(config, lookup, *, lookup_client_id, expected_developer_subject,
                              state, code_challenge, model, budget, expiry_days):
    """Reuse PKCE builder with server-obtained App Lookup evidence (offline only).

    A successful lookup proves app configuration, not attribution of any SK or
    an earnings credit. Do not expose this as a callback-less onboarding path.
    """
    if (not isinstance(lookup, dict)
            or lookup_client_id != config.client_id
            or not config.client_id.startswith("pk_")
            or config.authorize_url != DEFAULT_AUTHORIZE_URL
            or config.token_url != DEFAULT_TOKEN_URL
            or urlsplit(config.redirect_uri).scheme != "https"
            or not expected_developer_subject
            or lookup.get("found") is not True
            or lookup.get("userId") != expected_developer_subject
            or not isinstance(lookup.get("redirectUris"), list)
            or config.redirect_uri not in lookup["redirectUris"]
            or type(lookup.get("earningsEnabled")) is not bool
            or type(budget) is not int or not 0 < budget <= 10
            or type(expiry_days) is not int or not 1 <= expiry_days <= 7
            or not model):
        raise ValueError("Verified app owner, redirect and bounded OAuth request required")
    return {
        "authorization_url": build_authorization_url(
            config, state=state, code_challenge=code_challenge, models=model,
            budget=budget, expiry_days=expiry_days),
        "earnings_enabled_on_app": lookup["earningsEnabled"],
        "credential_attribution_verified": False,
        "earnings_confirmed": False,
        "cost_notice": "If eligible, developer earnings add 25% to base usage. "
                       "Self-use by the app owner is excluded. A trusted all-in quote is required.",
    }


def readiness(principal):
    from .execution_policy import generation_execution_authorized
    return {
        "pilot_role_eligible": principal.kind == "owner",
        "generation_enabled": False,
        "execution_policy_authorized": generation_execution_authorized(),
        "reason": ("Owner pilot eligible; pricing, consent, budget and execution gates still required"
                   if principal.kind == "owner" else
                   "Member generation disabled pending separate authorization"),
        "earnings": {
            "status": "UNVERIFIED_EXISTING_SK", "eligible": False,
            "confirmed": False, "amount_micro_pollen": None,
            "reason": "No verified App Key OAuth issuance link for this credential; "
                      "a personal SK or account ownership alone does not establish earnings eligibility. "
                      "App-owner self-use earns no markup.",
        },
        "total_cost_micro_pollen": None,
        "cost_status": "TRUSTED_ALL_IN_PRICING_UNAVAILABLE",
        "insufficient_balance": {
            "quests_url": QUESTS_URL, "automatic_redirect": False,
            "notice": "Provider 402 can mean account balance or key budget exhaustion. "
                      "Quests do not guarantee eligibility or sufficient balance; never auto-retry a started call.",
        },
    }
