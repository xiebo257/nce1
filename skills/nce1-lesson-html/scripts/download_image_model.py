#!/usr/bin/env python3
"""Resume verified FLUX.2 Klein weights from the ModelScope Chinese mirror."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import threading
from urllib.request import Request, urlopen


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda: f.read(4 * 1024**2), b''):
            h.update(buf)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path,
        default=Path.home()/'.cache/nce1-models/FLUX.2-Klein-4B-4bit')
    parser.add_argument('--workers', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error('--workers must be between 1 and 16')
    inventory = json.loads((Path(__file__).resolve().parent.parent /
                           'assets/flux2-klein-4b-model.json').read_text())
    root = args.destination
    root.mkdir(parents=True, exist_ok=True)
    # Prevent two downloader processes from corrupting the same range journal.
    import fcntl
    with (root / '.download.lock').open('w') as process_lock:
        fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tasks = []
        states = {}
        lock = threading.Lock()
        chunk = 16 * 1024**2
        for meta in inventory['files']:
            path = root / meta['Path']
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if path.stat().st_size == meta['Size'] and sha(path) == meta['Sha256']:
                    print('VERIFIED', meta['Path'], flush=True)
                    continue
                raise RuntimeError(f'Existing file does not match pinned checksum: {path}')
            part = path.with_name(path.name + '.part')
            journal = path.with_name(path.name + '.ranges.json')
            if journal.exists():
                state = json.loads(journal.read_text())
            else:
                # Without a journal a partial file is not a trusted contiguous prefix.
                state = {'prefix':0, 'done':[], 'sha256':meta['Sha256']}
            if state.get('sha256', meta['Sha256']) != meta['Sha256']:
                raise RuntimeError(f'Stale download journal: {journal}')
            states[meta['Path']] = (state, journal)
            for start in range(state['prefix'], meta['Size'], chunk):
                if start not in state['done']:
                    tasks.append((meta, start, min(start+chunk, meta['Size'])-1))

        def fetch(task):
            meta, start, end = task
            path = root / meta['Path']
            part = path.with_name(path.name + '.part')
            url = inventory['mirror'] + '/resolve/master/' + meta['Path']
            for attempt in range(4):
                try:
                    req = Request(url, headers={'Range':f'bytes={start}-{end}'})
                    with urlopen(req, timeout=60) as response:
                        whole = start == 0 and end == meta['Size']-1
                        valid_status = response.status == 206 or (whole and response.status == 200)
                        expected = f'bytes {start}-{end}/{meta["Size"]}'
                        content_range = response.headers.get('Content-Range')
                        valid_range = content_range == expected or (whole and content_range is None)
                        if not valid_status or not valid_range:
                            raise RuntimeError(f'Unexpected range response: {response.status} {content_range}')
                        data = response.read(end-start+2)
                    if len(data) != end-start+1:
                        raise RuntimeError('Incorrect response length')
                    fd = os.open(part, os.O_CREAT | os.O_WRONLY, 0o644)
                    try:
                        offset = 0
                        while offset < len(data):
                            offset += os.pwrite(fd, data[offset:], start+offset)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    with lock:
                        state, journal = states[meta['Path']]
                        state['done'].append(start)
                        tmp = journal.with_suffix('.tmp')
                        tmp.write_text(json.dumps(state))
                        tmp.replace(journal)
                        print('RANGE', meta['Path'], start, end, flush=True)
                    return
                except Exception:
                    if attempt == 3:
                        raise
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(fetch, tasks))
        for meta in inventory['files']:
            path = root / meta['Path']
            part = path.with_name(path.name + '.part')
            if not path.exists():
                if part.stat().st_size != meta['Size'] or sha(part) != meta['Sha256']:
                    raise RuntimeError(f'SHA256 verification failed: {part}')
                part.replace(path)
                path.with_name(path.name+'.ranges.json').unlink(missing_ok=True)
                print('VERIFIED', meta['Path'], flush=True)
        (root/'download-provenance.json').write_text(json.dumps(inventory, indent=2)+'\n')
        print('COMPLETE', root)


if __name__ == '__main__':
    main()
