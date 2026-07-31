import hashlib
import json
import os
import subprocess
import sys

PHOTOS_DIR = 'photos'
JSON_PATH = 'photos.json'
BUCKET = 'u-diary'
BUCKET_BASE = 'https://pub-af6cc2aa40a64382b17825de8e4a74e0.r2.dev'
WRANGLER = r'C:\Users\liu\AppData\Roaming\npm\wrangler.cmd'

def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def main():
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
    if not token:
        print('未设置 CLOUDFLARE_API_TOKEN')
        return 1

    files = []
    for fname in sorted(os.listdir(PHOTOS_DIR)):
        fpath = os.path.join(PHOTOS_DIR, fname)
        if not os.path.isfile(fpath): continue
        ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'): continue
        files.append((fname, fpath))

    print(f'本地照片: {len(files)} 张')
    print(f'开始上传到 R2...\n')

    entries = []
    ok = 0
    fail = []
    total = len(files)
    for i, (fname, fpath) in enumerate(files):
        ext = fname.lower().rsplit('.', 1)[-1]
        md5 = md5_file(fpath)
        key = f'{md5}.{ext}'
        r = subprocess.run(
            [WRANGLER, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', fpath, '--remote'],
            capture_output=True, encoding='utf-8', errors='replace',
        )
        if r.returncode == 0:
            ok += 1
            entries.append({
                'id': len(entries) + 1,
                'src': f'{BUCKET_BASE}/{key}',
                'date': '20XX.XX.XX',
                'cat': 'campus',
            })
        else:
            fail.append(fname)
        pct = (i + 1) / total * 100
        bar = '#' * (int(pct / 2)) + '-' * (50 - int(pct / 2))
        print(f'\r[{bar}] {i+1}/{total}  OK:{ok}  FAIL:{len(fail)}', end='', flush=True)

    print()

    if fail:
        print(f'\n失败 {len(fail)} 张，逐张重试...')
        for fname in fail:
            fpath = os.path.join(PHOTOS_DIR, fname)
            ext = fname.lower().rsplit('.', 1)[-1]
            md5 = md5_file(fpath)
            key = f'{md5}.{ext}'
            r = subprocess.run(
                [WRANGLER, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', fpath, '--remote'],
                capture_output=True, encoding='utf-8', errors='replace',
            )
            status = 'OK' if r.returncode == 0 else 'FAIL'
            print(f'  {fname}: {status}')
            if r.returncode == 0:
                entries.append({
                    'id': len(entries) + 1,
                    'src': f'{BUCKET_BASE}/{key}',
                    'date': '20XX.XX.XX',
                    'cat': 'campus',
                })

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f'\nphotos.json 已更新: {len(entries)} 条')
    print('完成！')
    return 0

if __name__ == '__main__':
    sys.exit(main())
