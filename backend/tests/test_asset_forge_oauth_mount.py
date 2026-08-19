from backend.asset_forge.main import app


def test_asset_forge_mounts_pollinations_oauth_routes():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/auth/pollinations")
    }

    assert any(path == "/auth/pollinations/login" and "GET" in methods for path, methods in routes)
    assert any(path == "/auth/pollinations/callback" and "GET" in methods for path, methods in routes)
    assert any(path == "/auth/pollinations/status" and "GET" in methods for path, methods in routes)
    assert any(path == "/auth/pollinations/logout" and "POST" in methods for path, methods in routes)
