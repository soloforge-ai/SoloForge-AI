"""Disposable PG17 + actual PostgREST; shared native isolation from PR214.

All JWTs/roles here are synthetic. No URL, DSN or credentials are accepted from
production environment variables. PostgREST binds only a local Unix socket.
"""
import ast
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import httpx
from cloudflare_native_fixture import connection, disposable_database, SOCKET

ROOT = Path(__file__).resolve().parents[3]
JWT_SECRET = b'OFFLINE-POLLINATIONS-REST-FIXTURE-ONLY-32-BYTES'


def legacy_schema():
    tree = ast.parse(Path(__file__).with_name('test_pollinations_owner_binding.py').read_text())
    legacy = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
        and isinstance(n.value, str) and 'create schema auth;' in n.value)
    return (ROOT/'supabase/migrations/20261024151629_owner_identity_v2.sql').read_text()+legacy+'''
    alter table public.pollinations_sessions enable row level security;
    revoke all on public.pollinations_sessions from public,anon,authenticated;
    grant select,insert,update on public.pollinations_sessions to service_role;
    '''


def execute_ddl(db, statement):
    # Each script has its own physical connection; failed explicit BEGIN rolls
    # back on close. Never continue a failed transaction or silently replay it.
    if statement.strip().lower() == 'rollback':
        return
    try:
        with connection(db.name, autocommit=True) as conn:
            conn.execute(statement, prepare=False)
    except Exception as exc:
        primary = getattr(getattr(exc,'diag',None),'message_primary','') or ''
        for allowed in ('Duplicate credentials','Already or partially migrated',
                        'Unexpected legacy constraint','Unexpected legacy insert guard'):
            if primary.startswith(allowed):
                raise RuntimeError(allowed+'; migration rejected') from None
        raise RuntimeError('Native migration failed: '+str(getattr(exc,'sqlstate','unknown'))) from None


def jwt(role='service_role', *, subject=None):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).rstrip(b'=')
    claims={'role':role,'exp':int(time.time())+300}
    if subject: claims['sub']=subject
    message=encode({'alg':'HS256','typ':'JWT'})+b'.'+encode(claims)
    signature=base64.urlsafe_b64encode(hmac.new(JWT_SECRET,message,hashlib.sha256).digest()).rstrip(b'=')
    return (message+b'.'+signature).decode()


@contextmanager
def rest_service(db):
    binary=Path(os.environ['POLLINATIONS_TEST_POSTGREST_BIN'])
    assert binary.is_file() and binary.name == 'postgrest'
    with connection(autocommit=True) as conn:
        if not conn.execute("select 1 from pg_roles where rolname='oauth_test_authenticator'").fetchone():
            conn.execute('create role oauth_test_authenticator login noinherit nosuperuser nobypassrls')
        conn.execute('grant anon,authenticated,service_role to oauth_test_authenticator')
        flags=conn.execute("select rolsuper,rolbypassrls,rolinherit from pg_roles where rolname='oauth_test_authenticator'").fetchone()
        assert flags == (False,False,False)
    with tempfile.TemporaryDirectory(prefix='pollinations-rest-') as directory:
        socket=str(Path(directory)/'api.sock')
        env={k:os.environ[k] for k in ('PATH','LANG') if k in os.environ}
        env.update(PGRST_DB_URI='postgresql://oauth_test_authenticator@/'+db.name+'?host='+SOCKET,
            PGRST_DB_SCHEMAS='public',PGRST_DB_ANON_ROLE='anon',PGRST_DB_CONFIG='false',
            PGRST_JWT_SECRET=JWT_SECRET.decode(),PGRST_SERVER_UNIX_SOCKET=socket,
            PGRST_SERVER_UNIX_SOCKET_MODE='600',PGRST_LOG_LEVEL='crit',
            PGRST_DB_POOL='3',PGRST_DB_CHANNEL_ENABLED='true')
        process=subprocess.Popen([str(binary),'+RTS','-N1','-RTS'],env=env,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        client=httpx.Client(transport=httpx.HTTPTransport(uds=socket),base_url='http://isolated.test',trust_env=False,timeout=5)
        try:
            deadline=time.monotonic()+20
            while True:
                if process.poll() is not None: raise RuntimeError('Disposable PostgREST exited during startup')
                try:
                    response=client.get('/')
                    if response.status_code==200: break
                except httpx.TransportError: pass
                if time.monotonic()>deadline: raise RuntimeError('Disposable PostgREST startup timed out')
                time.sleep(.1)
            yield client
        finally:
            client.close()
            process.terminate()
            try: process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(5)


def reload_schema(db, client):
    db.query("notify pgrst, 'reload schema'")
    deadline=time.monotonic()+15
    while True:
        response=client.get('/pollinations_sessions',params={'select':'submitted_by_owner','limit':0},
            headers={'Authorization':'Bearer '+jwt()})
        if response.status_code==200: return
        if time.monotonic()>deadline: raise RuntimeError('PostgREST schema refresh not established')
        time.sleep(.1)
