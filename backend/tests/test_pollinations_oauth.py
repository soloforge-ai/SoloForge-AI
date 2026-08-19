from urllib.parse import parse_qs, urlparse
import backend.pollinations_oauth as oauth

def test_pkce_transaction_shapes():
    verifier, challenge, state = oauth.create_pkce_transaction()
    assert len(verifier) >= 43
    assert challenge and state
    assert "=" not in challenge

def test_authorization_url_contains_required_oauth_parameters():
    config = oauth.PollinationsOAuthConfig(client_id="pk_test", redirect_uri="https://example.com/auth/pollinations/callback")
    query = parse_qs(urlparse(oauth.build_authorization_url(config, code_challenge="challenge", state="state")).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["pk_test"]
    assert query["redirect_uri"] == [config.redirect_uri]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["state"]
