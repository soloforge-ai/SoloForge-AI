"""Credential-free native/PostgREST runner, PR214's Unix-only confinement."""
import os
from pathlib import Path
import subprocess
from run_cloudflare_native import isolate

if __name__=='__main__':
    binary=Path(os.environ['POLLINATIONS_TEST_POSTGREST_BIN']).resolve()
    if binary.name!='postgrest' or not binary.is_file():
        raise RuntimeError('Pinned isolated PostgREST binary required')
    version=subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True,timeout=5).stdout
    if '16.5' not in version:
        raise RuntimeError('Verified PostgREST version required')
    isolate()  # clears credentials, denies non-Unix sockets, checks PG network.
    os.environ['POLLINATIONS_TEST_POSTGREST_BIN']=str(binary)
    print('PostgREST 16.5 verified; native PG17 and REST over Unix sockets only',flush=True)
    import pytest
    raise SystemExit(pytest.main(['-q','-rA','--tb=short','-p','no:cacheprovider',
        str(Path(__file__).with_name('pollinations_native_cases.py'))]))
