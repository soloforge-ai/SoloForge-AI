"""Native TestClient coverage for isolated CI; NOT RUN in this restricted sandbox.

No skips or production dependencies. Reuses the same assertions and fakes as the
locally executed ASGI slice, with normal HTTP threadpool scheduling. Deliberate
SystemExit is tested at the local ASGI boundary, not in TestClient's portal.
"""
import pytest
from fastapi.testclient import TestClient
from test_byop_owner_pilot import (
    pilot, persistent, byop_db, binding_db,
    test_owner_http_pilot_success_private_preview_and_a_b_binding as test_native_owner_success,
    test_http_invalid_permit_denies_before_dispatch as test_native_invalid_permit,
    test_http_owner_permit_never_enables_member_or_foreign_access as test_native_member_denial,
    test_http_dispatch_evidence_or_identity_failure_closed as test_native_evidence_denial,
    test_http_ambiguous_result_or_crash_never_replays as _ambiguous,
)


@pytest.fixture
def http(pilot):
    with TestClient(pilot['app']) as client:
        def send(method, path, **kwargs):
            kwargs.setdefault('headers', {'Authorization': pilot['header']})
            return client.request(method, '/v1/byop'+path, **kwargs)
        yield send


def test_native_timeout_retains_reservation_without_replay(pilot, http):
    _ambiguous(pilot, http, 'timeout', 'UNKNOWN')
