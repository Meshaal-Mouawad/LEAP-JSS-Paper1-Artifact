#!/usr/bin/env python3
"""Verify the exact technical reviewer archive without changing it."""
from pathlib import Path
import hashlib, json, sys, unicodedata
ROOT=Path(__file__).resolve().parent

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((ROOT/'ARTIFACT_MANIFEST.json').read_text())
    actual={}
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT).as_posix()
        if any(x in {'.git','__pycache__','__MACOSX'} for x in p.relative_to(ROOT).parts) or p.name=='.DS_Store':
            continue
        if p.is_symlink():
            raise ValueError('Symbolic link in artifact: '+rel)
        if not p.is_file() or rel=='ARTIFACT_MANIFEST.json':
            continue
        key=unicodedata.normalize('NFC',rel)
        if key in actual:
            raise ValueError('Ambiguous Unicode path: '+rel)
        actual[key]=p
    expected={}
    for rel,row in manifest['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('Unsafe manifest path: '+rel)
        key=unicodedata.normalize('NFC',rel)
        if key in expected:
            raise ValueError('Ambiguous manifest path: '+rel)
        expected[key]=row
    failures=[]
    for key,row in expected.items():
        p=actual.get(key)
        if p is None or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:
            failures.append(key)
    extra=sorted(set(actual)-set(expected))
    missing=sorted(set(expected)-set(actual))
    ok=not failures and not extra and not missing
    print(json.dumps({'status':'PASS' if ok else 'FAIL','verified_entries':len(expected),
                      'hash_failures':failures,'extra':extra,'missing':missing,
                      'path_comparison':'Unicode NFC; unique paths required',
                      'software_executed':False,'files_modified':False},indent=2))
    return 0 if ok else 1
if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError,KeyError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);sys.exit(1)
