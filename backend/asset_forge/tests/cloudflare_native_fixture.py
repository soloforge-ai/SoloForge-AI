"""Native PG17 adapter for the existing sanitized persistence contracts, CI only."""
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from uuid import UUID, uuid4

SOCKET = '/tmp/soloforge-cloudflare-native-socket'
ROLES = {'postgres', 'anon', 'authenticated', 'service_role'}


def connection(database='cloudflare_ci', *, autocommit=False):
    import psycopg
    # No DSN/env/host input is accepted. Refuse TCP and inherited credentials.
    if os.environ.get('CF_NATIVE_ISOLATED') != '1':
        raise RuntimeError('Isolated native runner required')
    if database != 'cloudflare_ci' and not re.fullmatch(r'cf_native_[0-9a-f]{32}', database):
        raise RuntimeError('Disposable database required')
    if not stat.S_ISSOCK(Path(SOCKET, '.s.PGSQL.5432').stat().st_mode):
        raise RuntimeError('Private PostgreSQL Unix socket required')
    conn = psycopg.connect(host=SOCKET, dbname=database, user='postgres', password='',
        connect_timeout=3, autocommit=autocommit, options='-c statement_timeout=15000 -c lock_timeout=5000')
    if not 170000 <= conn.info.server_version < 180000:
        conn.close()
        raise RuntimeError('PostgreSQL 17 required')
    return conn


def _json(value):
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, UUID): return str(value)
    if isinstance(value, Decimal): return float(value)
    raise TypeError('Unsupported SQL result')


class NativeDatabase:
    def __init__(self, name):
        self.name = name

    def call(self, name, body):
        args = ','.join(f'{key} => ${i}' for i, key in enumerate(body, 1))
        return self.query(f'select public.owner_v2_{name}({args}) as value',
            list(body.values()), 'service_role')[0]['value']

    def query(self, statement, params=(), role='postgres'):
        from psycopg import sql
        from psycopg.rows import dict_row
        if role not in ROLES: raise RuntimeError('Invalid role')
        # One NEW physical connection per call, no global lock/shared transaction.
        query = re.sub(r'\$(\d+)\b', lambda m: '%(p'+m[1]+')s', statement)
        values = {'p'+str(i): v for i, v in enumerate(params, 1)}
        try:
            with connection(self.name) as conn:
                conn.row_factory = dict_row
                conn.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                cursor = conn.execute(query, values if params else None, prepare=False)
                rows = cursor.fetchall() if cursor.description else []
                return json.loads(json.dumps(rows, default=_json))
        except Exception as exc:
            # SQLSTATE is useful diagnostics without params/key/ciphertext.
            code=getattr(exc,'sqlstate',None) or 'unavailable'
            raise RuntimeError('Native fixture transaction failed: '+code) from None


def container_id():
    value = os.environ.get('CF_NATIVE_CONTAINER', '')
    if not re.fullmatch(r'[0-9a-f]{12,64}', value):
        raise RuntimeError('Dedicated CI service container required')
    return value


def assert_container_isolation():
    cid = container_id()
    for expression in ('{{json .NetworkSettings.Networks}}', '{{json .HostConfig.PortBindings}}'):
        result = subprocess.run(['docker','--host=unix:///var/run/docker.sock','inspect',
            '--format',expression,cid], check=True,capture_output=True,text=True,timeout=10)
        if json.loads(result.stdout) not in ({}, None):
            raise RuntimeError('PostgreSQL must have no networks or published ports')


def restart_service():
    assert_container_isolation()
    subprocess.run(['docker','--host=unix:///var/run/docker.sock','restart','--time','10',container_id()],
        check=True,capture_output=True,timeout=30)
    assert_container_isolation()
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        try:
            with connection() as conn: conn.execute('select 1')
            return
        except Exception:
            time.sleep(.2)
    raise RuntimeError('Native PostgreSQL restart failed')


@contextmanager
def disposable_database(schema):
    from psycopg import sql
    assert_container_isolation()
    name='cf_native_'+uuid4().hex
    with connection(autocommit=True) as admin:
        # Roles are local to the dedicated disposable CI cluster.
        for role in ('anon','authenticated','service_role'):
            if not admin.execute('select 1 from pg_roles where rolname=%s',(role,)).fetchone():
                admin.execute(sql.SQL('create role {} nologin {}').format(sql.Identifier(role),
                    sql.SQL('bypassrls' if role=='service_role' else '')))
        admin.execute(sql.SQL('create database {}').format(sql.Identifier(name)))
    try:
        with connection(name,autocommit=True) as conn:
            conn.execute(schema,prepare=False)
        holder={'db':NativeDatabase(name)}
        def boot(reopen=False):
            if not reopen: raise RuntimeError('Use disposable schema initialization')
            with connection(name) as conn:
                before=conn.execute('select pg_postmaster_start_time()').fetchone()[0]
            restart_service()  # Actual PostgreSQL process restart, not reconnect.
            with connection(name) as conn:
                after=conn.execute('select pg_postmaster_start_time()').fetchone()[0]
            if not after>before: raise RuntimeError('Postmaster restart not established')
            return NativeDatabase(name)
        holder['boot']=boot
        yield holder
    finally:
        with connection(autocommit=True) as admin:
            admin.execute(sql.SQL('drop database {} with (force)').format(sql.Identifier(name)))
