import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image

PHOTOS_DIR = 'photos'
JSON_PATH = 'photos.json'
BUCKET = 'u-diary'
BUCKET_BASE = 'https://pub-af6cc2aa40a64382b17825de8e4a74e0.r2.dev'
WRANGLER = r'C:\Users\liu\AppData\Roaming\npm\wrangler.cmd'
THUMB_MAX = 1000
THUMB_QUALITY = 82

SRC_RE = re.compile(r'/([0-9a-f]{32})\.\w+$')

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

    with open(JSON_PATH, encoding='utf-8') as f:
        entries = json.load(f)

    by_md5 = {}
    for idx, e in enumerate(entries):
        m = SRC_RE.search(e.get('src', ''))
        if m:
            by_md5.setdefault(m.group(1), []).append(idx)

    files = []
    for fname in sorted(os.listdir(PHOTOS_DIR)):
        fpath = os.path.join(PHOTOS_DIR, fname)
        if not os.path.isfile(fpath): continue
        ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'): continue
        files.append((fname, fpath))

    print(f'本地照片: {len(files)} 张, photos.json: {len(entries)} 条\n')

    ok = skip = 0
    fail = []
    total = len(files)
    tmp = tempfile.gettempdir()

    for i, (fname, fpath) in enumerate(files):
        md5 = md5_file(fpath)
        idxs = by_md5.get(md5)
        if not idxs:
            fail.append(f'{fname}: 未在 photos.json 找到对应条目')
            continue
        idx = idxs[0]
        entry = entries[idx]
        if entry.get('thumb'):
            skip += 1
        else:
            key = f'thumbs/{md5}.webp'
            tmp_path = os.path.join(tmp, f'_thumb_{md5}.webp')
            try:
                with Image.open(fpath) as im:
                    im = im.convert('RGB')
                    im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
                    im.save(tmp_path, 'WEBP', quality=THUMB_QUALITY, method=4)
            except Exception as ex:
                fail.append(f'{fname}: 生成失败 {ex}')
                continue
            r = subprocess.run(
                [WRANGLER, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', tmp_path,
                 '--content-type', 'image/webp', '--remote'],
                capture_output=True, encoding='utf-8', errors='replace',
            )
            if r.returncode == 0:
                entry['thumb'] = f'{BUCKET_BASE}/{key}'
                ok += 1
            else:
                fail.append(f'{fname}: 上传失败')
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        pct = (i + 1) / total * 100
        bar = '#' * (int(pct / 2)) + '-' * (50 - int(pct / 2))
        print(f'\r[{bar}] {i+1}/{total}  OK:{ok}  SKIP:{skip}  FAIL:{len(fail)}', end='', flush=True)

    print()

    if ok:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f'photos.json 已更新: 新增 {ok} 个 thumb 字段')

    if fail:
        print(f'\n失败 {len(fail)} 项:')
        for msg in fail:
            print('  ' + msg)
        print('修复后可重跑（已生成的会跳过）')

    print(f'完成！新增 {ok} 上传, {skip} 跳过, {len(fail)} 失败')
    return 0 if not fail else 2

if __name__ == '__main__':
    sys.exit(main())
