import hashlib
import io
import json
import os
import re
import sys
import urllib.request

from PIL import Image, ImageOps

PHOTOS_DIR = 'photos'
JSON_PATH = 'photos.json'
BUCKET = 'u-diary'
BUCKET_BASE = 'https://pub-af6cc2aa40a64382b17825de8e4a74e0.r2.dev'
ACCOUNT = 'ee871b8cbf20439246b232b0ff91ee83'
OBJ_API = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/r2/buckets/{BUCKET}/objects'

THUMB_W = 1000   # 4:3 裁切后宽
THUMB_H = 750
FULL_MAX = 1600
QUALITY = 82
VERSION = 3

SRC_RE = re.compile(r'/([0-9a-f]{32})\.\w+$')

def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def upload(key, data, ctype):
    req = urllib.request.Request(f'{OBJ_API}/{key}', data=data, method='PUT')
    req.add_header('Authorization', 'Bearer ' + os.environ.get('CLOUDFLARE_API_TOKEN', ''))
    req.add_header('Content-Type', ctype)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False

def crop_4_3(im):
    w, h = im.size
    target = THUMB_W / THUMB_H
    cur = w / h
    if cur > target:
        nw = int(round(h * target))
        x = (w - nw) // 2
        box = (x, 0, x + nw, h)
    else:
        nh = int(round(w / target))
        y = (h - nh) // 2
        box = (0, y, w, y + nh)
    return im.crop(box)

def to_webp(im):
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=QUALITY, method=4)
    return buf.getvalue()

def main():
    if not os.environ.get('CLOUDFLARE_API_TOKEN'):
        print('未设置 CLOUDFLARE_API_TOKEN')
        return 1

    with open(JSON_PATH, encoding='utf-8') as f:
        entries = json.load(f)

    files = []
    for fname in sorted(os.listdir(PHOTOS_DIR)):
        fpath = os.path.join(PHOTOS_DIR, fname)
        if not os.path.isfile(fpath): continue
        ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'): continue
        files.append((fname, fpath))

    md5_map = {md5_file(fp): fp for _, fp in files}
    print(f'本地照片: {len(files)} 张\n')

    ok = skip = 0
    fail = []
    total = len(files)

    for i, (fname, fpath) in enumerate(files):
        md5 = md5_file(fpath)
        entry = next((e for e in entries if e.get('thumb', '').find(md5) >= 0), None)
        if not entry:
            fail.append(f'{fname}: 未在 photos.json 找到对应条目')
            continue

        thumb_key = f'thumbs/{md5}.webp'
        full_key = f'full/{md5}.webp'
        thumb_url = f'{BUCKET_BASE}/{thumb_key}?v={VERSION}'
        full_url = f'{BUCKET_BASE}/{full_key}?v={VERSION}'

        if entry.get('thumb') == thumb_url and entry.get('full') == full_url:
            skip += 1
        else:
            try:
                with Image.open(fpath) as im0:
                    im = ImageOps.exif_transpose(im0).convert('RGB')

                    t = crop_4_3(im).resize((THUMB_W, THUMB_H), Image.LANCZOS)
                    if not upload(thumb_key, to_webp(t), 'image/webp'):
                        fail.append(f'{fname}: thumb 上传失败')
                        continue

                    f = im.copy()
                    f.thumbnail((FULL_MAX, FULL_MAX), Image.LANCZOS)
                    if not upload(full_key, to_webp(f), 'image/webp'):
                        fail.append(f'{fname}: full 上传失败')
                        continue

                    entry['thumb'] = thumb_url
                    entry['full'] = full_url
                    with open(JSON_PATH, 'w', encoding='utf-8') as f:
                        json.dump(entries, f, ensure_ascii=False, indent=2)
                    ok += 1
            except Exception as ex:
                fail.append(f'{fname}: 生成失败 {ex}')
                continue

        pct = (i + 1) / total * 100
        bar = '#' * (int(pct / 2)) + '-' * (50 - int(pct / 2))
        print(f'\r[{bar}] {i+1}/{total}  OK:{ok}  SKIP:{skip}  FAIL:{len(fail)}', end='', flush=True)

    print()

    if ok:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f'photos.json 已更新: 处理 {ok} 张（thumb/full 均带 ?v={VERSION}）')

    if fail:
        print(f'\n失败 {len(fail)} 项:')
        for msg in fail:
            print('  ' + msg)

    print(f'完成！新增 {ok} 上传, {skip} 跳过, {len(fail)} 失败')
    return 0 if not fail else 2

if __name__ == '__main__':
    sys.exit(main())
