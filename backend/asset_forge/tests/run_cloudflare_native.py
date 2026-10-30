"""Manual CI runner: credential-free env, Unix sockets only, no provider egress."""
import ctypes
import ctypes.util
import errno
import os
from pathlib import Path
import socket
import sys


def isolate():
    if os.environ.get('GITHUB_ACTIONS')!='true':
        raise RuntimeError('Dedicated manual CI job required')
    allowed={k:os.environ[k] for k in ('PATH','PYTHONPATH','LANG','TMPDIR','CF_NATIVE_CONTAINER') if k in os.environ}
    os.environ.clear(); os.environ.update(allowed)
    os.environ.update(CF_NATIVE_ISOLATED='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
    for fd in Path('/proc/self/fd').iterdir():
        try: target=os.readlink(fd)
        except FileNotFoundError: continue
        if target.startswith('socket:'): raise RuntimeError('Inherited socket denied')
    name=ctypes.util.find_library('seccomp')
    if not name: raise RuntimeError('libseccomp required')
    lib=ctypes.CDLL(name)
    class Compare(ctypes.Structure):
        _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_int),('a',ctypes.c_uint64),('b',ctypes.c_uint64)]
    lib.seccomp_init.argtypes=[ctypes.c_uint32]; lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]; lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Compare)]
    lib.seccomp_load.argtypes=[ctypes.c_void_p]; lib.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx=lib.seccomp_init(0x7fff0000)
    if not ctx: raise RuntimeError('seccomp unavailable')
    try:
        for syscall in (b'socket',b'socketpair',b'io_uring_setup'):
            number=lib.seccomp_syscall_resolve_name(syscall)
            if number<0: raise RuntimeError('Unknown syscall')
            comparison=Compare(0,1,socket.AF_UNIX,0)  # SCMP_CMP_NE: deny non-Unix sockets
            count=0 if syscall==b'io_uring_setup' else 1
            if lib.seccomp_rule_add_array(ctx,0x50000|errno.EPERM,number,count,
                    None if count==0 else ctypes.byref(comparison))!=0:
                raise RuntimeError('Cannot establish network isolation')
        if lib.seccomp_load(ctx)!=0: raise RuntimeError('Cannot load seccomp')
    finally: lib.seccomp_release(ctx)
    for family in (socket.AF_INET,socket.AF_INET6):
        for kind in (socket.SOCK_STREAM,socket.SOCK_DGRAM):
            try:
                with socket.socket(family,kind): pass
            except PermissionError: continue
            raise RuntimeError('External socket unexpectedly allowed')
    from cloudflare_native_fixture import assert_container_isolation
    assert_container_isolation()
    print('ISOLATION PASS: credentials cleared; only Unix sockets allowed; PostgreSQL has no network or published ports',flush=True)


if __name__=='__main__':
    isolate()
    import pytest
    raise SystemExit(pytest.main(['-q','-rA','--tb=short','-p','no:cacheprovider',
        str(Path(__file__).with_name('cloudflare_native_cases.py')),
        str(Path(__file__).with_name('cloudflare_application_native_cases.py')),
        str(Path(__file__).with_name('test_cloudflare_image.py'))]))
