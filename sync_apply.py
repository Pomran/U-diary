import hashlib
import json
import os
import subprocess
import sys
import time

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
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
    if not token:
        print('错误: 请先设置 $env:CLOUDFLARE_API_TOKEN')
        return 1

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        old_entries = json.load(f)

    local = []
    seen_md5 = {}
    for fname in sorted(os.listdir(PHOTOS_DIR)):
        fpath = os.path.join(PHOTOS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'):
            continue
        content_md5 = md5_file(fpath)
        if content_md5 in seen_md5:
            continue
        seen_md5[content_md5] = fname
        local.append({
            'fname': fname, 'fpath': fpath, 'content_md5': content_md5, 'ext': ext,
            'date': '20XX.XX.XX', 'cat': 'campus',
        })

    print(f"本地: {len(local)} 张")

    # Check which are already in R2
    need_upload = []
    skip = 0
    fail_verify = 0
    for item in local:
        url = f"{BUCKET_BASE}/{item['content_md5']}.{item['ext']}"
        r = subprocess.run(['curl.exe', '-s', '-o', 'NUL', '-w', '%{http_code}', url],
                          capture_output=True, encoding='utf-8', errors='replace')
        if r.stdout.strip() == '200':
            skip += 1
        else:
            need_upload.append(item)

    print(f"R2 已有: {skip} 张, 需上传: {len(need_upload)} 张")

    if not need_upload:
        print("全部已在 R2!")
        # Update photos.json
        new_entries = [{'id': i+1, 'src': f"{BUCKET_BASE}/{l['content_md5']}.{l['ext']}", 'date': l['date'], 'cat': l['cat']} for i, l in enumerate(local)]
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_entries, f, ensure_ascii=False, indent=2)
        print(f"photos.json: {len(new_entries)} 条")
        return 0

    # Single-threaded upload
    ok = 0
    fail_items = []
    total = len(need_upload)
    for i, item in enumerate(need_upload):
        key = f"{item['content_md5']}.{item['ext']}"
        r = subprocess.run(
            [WRANGLER, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', item['fpath'], '--remote'],
            capture_output=True, encoding='utf-8', errors='replace',
        )
        if r.returncode == 0 and 'Upload complete' in r.stdout:
            ok += 1
        else:
            fail_items.append(item)
        eta = ''
        if i > 0:
            elapsed = time.time() - t0
            per = elapsed / (i+1)
            eta = f'  预计剩余 {int((total-i-1)*per)}s'
        if i == 0:
            t0 = time.time()
        print(f"\r[{i+1}/{total}]  成功 {ok}  失败 {len(fail_items)}{eta}", end='', flush=True)

    print()

    if fail_items:
        print(f"\n失败 {len(fail_items)} 张，重试一次...")
        for item in fail_items:
            key = f"{item['content_md5']}.{item['ext']}"
            r = subprocess.run(
                [WRANGLER, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', item['fpath'], '--remote'],
                capture_output=True, encoding='utf-8', errors='replace',
            )
            print(f"  {item['fname']}: {'OK' if r.returncode==0 and 'Upload complete' in r.stdout else 'FAIL'}")

    # Write photos.json
    new_entries = [{'id': i+1, 'src': f"{BUCKET_BASE}/{l['content_md5']}.{l['ext']}", 'date': l['date'], 'cat': l['cat']} for i, l in enumerate(local)]
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_entries, f, ensure_ascii=False, indent=2)
    print(f"\nphotos.json 已更新: {len(new_entries)} 条\ndate/cat 为默认值，可在 photos.json 中手动修改")
    return 0

if __name__ == '__main__':
    sys.exit(main())
