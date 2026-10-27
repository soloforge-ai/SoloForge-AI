"""Pure offline provider contract/readiness; no network or socketpair required."""
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit
import pytest
from fastapi import HTTPException
from backend.byop_flow import Flow
from backend.byop_principal import Principal, require_generation_role
from backend.byop_router import session, get_flow
from backend.pollinations_app_contract import prepare_app_authorization, readiness
from backend.pollinations_oauth import PollinationsOAuthConfig


CONFIG = PollinationsOAuthConfig('pk_offline_fixture', 'https://app.example.test/callback')
LOOKUP = {'found': True, 'userId': 'developer-fixture',
          'redirectUris': [CONFIG.redirect_uri], 'earningsEnabled': True}


def prepare(config=CONFIG, lookup=None, budget=1):
    return prepare_app_authorization(config, LOOKUP if lookup is None else lookup,
        lookup_client_id=CONFIG.client_id, expected_developer_subject='developer-fixture', state='offline-csrf-state',
        code_challenge='offline-pkce-challenge', model='kontext', budget=budget, expiry_days=1)


def test_documented_oauth_link_prefill_limit_is_enforced_offline():
    assert parse_qs(urlsplit(prepare(budget=10)['authorization_url']).query)['budget'] == ['10']
    with pytest.raises(ValueError):
        prepare(budget=11)


def test_app_contract_reuses_pkce_without_claiming_earnings():
    result = prepare()
    url = urlsplit(result['authorization_url'])
    assert url.scheme == 'https' and url.netloc == 'enter.pollinations.ai'
    params = parse_qs(url.query)
    assert params['client_id'] == [CONFIG.client_id]
    assert params['response_type'] == ['code'] and params['code_challenge_method'] == ['S256']
    assert params['budget'] == ['1'] and params['models'] == ['kontext']
    assert result['earnings_enabled_on_app'] is True
    assert result['credential_attribution_verified'] is False
    assert result['earnings_confirmed'] is False


@pytest.mark.parametrize('change', [
    {'found': False}, {'userId': 'foreign-developer'}, {'redirectUris': []},
    {'earningsEnabled': 'true'}, {'redirectUris': CONFIG.redirect_uri},
])
def test_app_contract_rejects_untrusted_attribution(change):
    with pytest.raises(ValueError):
        prepare(lookup={**LOOKUP, **change})


@pytest.mark.parametrize('change', [
    {'client_id': 'sk_not_an_app'}, {'client_id': 'pk_different_app'},
    {'authorize_url': 'https://untrusted.example.test/authorize'},
    {'token_url': 'https://untrusted.example.test/token'}, {'redirect_uri': 'http://app.example.test/callback'},
])
def test_app_contract_rejects_wrong_client_and_origins(change):
    with pytest.raises(ValueError):
        prepare(config=replace(CONFIG, **change))


@pytest.mark.parametrize('kind', ['owner', 'member'])
def test_readiness_never_claims_live_generation_cost_or_earnings(kind):
    result = readiness(Principal(kind, 'fixture'))
    assert result['pilot_role_eligible'] is (kind == 'owner')
    assert result['generation_enabled'] is False
    assert result['execution_policy_authorized'] is False
    assert result['total_cost_micro_pollen'] is None
    assert result['earnings']['eligible'] is False and result['earnings']['confirmed'] is False
    assert result['earnings']['amount_micro_pollen'] is None
    assert result['insufficient_balance']['quests_url'] == 'https://enter.pollinations.ai/quests'
    assert result['insufficient_balance']['automatic_redirect'] is False


def test_real_application_construction_keeps_owner_only_policy():
    flow = get_flow()
    assert flow.generation_policy is require_generation_role
    assert flow.generation_policy(Principal('owner', 'fixture')) is None
    with pytest.raises(HTTPException):
        flow.generation_policy(Principal('member', 'fixture'))


def test_default_flow_denies_member_before_touching_ledger():
    flow = Flow(lambda _: Principal('member', 'fixture'), None, None, None, None)
    with pytest.raises(HTTPException) as exc:
        flow.execute('offline', 'consent', 'execution')
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        flow.authorize('offline', 'credential', 'job', 1, 1)
    assert exc.value.status_code == 403


def test_session_exposes_readiness_without_granting_spend():
    flow = Flow(lambda _: Principal('owner', 'fixture'), None, None, None, None)
    result = session('offline', flow)
    assert result['spending_authorized'] is False
    assert result['readiness']['pilot_role_eligible'] is True
