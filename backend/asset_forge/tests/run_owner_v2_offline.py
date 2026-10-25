"""Run V2 tests in Linux seccomp confinement, with a credential-free environment.

Dependencies must be installed BEFORE this runner. All descendant processes inherit
the filter. AF_UNIX socketpair is retained for TestClient's in-process event loop;
new socket/connect/accept and io_uring syscalls are denied by the kernel.
"""
import ctypes
import ctypes.util
import errno
import os
from pathlib import Path
import socket
import sys


def isolate():
    allowed = {key: os.environ[key] for key in (
        "PATH", "PYTHONPATH", "OWNER_V2_TEST_PGLITE", "LANG", "TMPDIR"
    ) if key in os.environ}
    os.environ.clear()
    os.environ.update(allowed)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    # Reject inherited sockets, rather than assuming socket creation denial alone
    # closes existing descriptors. Subprocess test bridges inherit pipes only.
    for fd in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith("socket:"):
            raise RuntimeError("Inherited socket: refuse offline run")
    library = ctypes.util.find_library("seccomp")
    if not library:
        raise RuntimeError("libseccomp required; no weaker fallback")
    lib = ctypes.CDLL(library)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError("Cannot create seccomp context")
    try:
        for name in (b"socket", b"connect", b"accept", b"accept4", b"io_uring_setup"):
            number = lib.seccomp_syscall_resolve_name(name)
            if number < 0 or lib.seccomp_rule_add(context, 0x50000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("Cannot install network denial rule")
        if lib.seccomp_load(context) != 0:
            raise RuntimeError("Cannot load network denial filter")
    finally:
        lib.seccomp_release(context)
    for family in (socket.AF_INET, socket.AF_INET6):
        for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            try:
                with socket.socket(family, kind):
                    pass
            except PermissionError:
                continue
            raise RuntimeError("Network denial probe failed")
    print("ISOLATION PASS: seccomp denied IPv4/IPv6 TCP/UDP sockets; credentials cleared", flush=True)


if __name__ == "__main__":
    isolate()
    import pytest
    raise SystemExit(pytest.main([
        "-q", "-p", "no:cacheprovider", str(Path(__file__).with_name("test_owner_v2.py")), *sys.argv[1:]
    ]))
