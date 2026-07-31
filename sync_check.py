import hashlib
import json
import os
import sys

PHOTOS_DIR = 'photos'
JSON_PATH = 'photos.json'

def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(16384)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def md5_from_src(src):
    filename = src.rsplit('/', 1)[-1]
    return filename.rsplit('.', 1)[0] if '.' in filename else filename

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    entries = json.load(f)

existing_md5s = {md5_from_src(e['src']): e for e in entries}

local_files = {}
dupes = []
missing_file = 0
for fname in sorted(os.listdir(PHOTOS_DIR)):
    fpath = os.path.join(PHOTOS_DIR, fname)
    if not os.path.isfile(fpath):
        continue
    ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'):
        continue
    try:
        md5 = md5_file(fpath)
    except OSError as e:
        print(f"  SKIP 读取失败: {fname} ({e})")
        continue
    if md5 in local_files:
        dupes.append(f"  {fname}  与  {local_files[md5]['name']}  内容相同 (MD5: {md5[:12]}...)")
        continue
    local_files[md5] = {'name': fname, 'path': fpath}

new_files = {md5: info for md5, info in local_files.items() if md5 not in existing_md5s}
deleted = {md5: existing_md5s[md5] for md5 in existing_md5s if md5 not in local_files}

print(f"本地照片文件: {len(local_files)} 张")
print(f"photos.json    : {len(entries)} 条")
print(f"  ├─ 新增 (需上传 R2) : {len(new_files)} 张")
print(f"  ├─ 已删除 (本地不存在) : {len(deleted)} 条")
print(f"  └─ 重复文件 (已跳过)   : {len(dupes)} 个")
if len(local_files) != len(entries):
    print(f"  ✓ 同步后将是 {len(entries) - len(deleted) + len(new_files)} 条")

if dupes:
    print(f"\n重复文件 ({len(dupes)}):")
    for d in dupes[:10]:
        print(d)
    if len(dupes) > 10:
        print(f"  ... 等 {len(dupes)-10} 个")

if new_files:
    print(f"\n新增文件 ({len(new_files)}):")
    for i, (md5, info) in enumerate(list(new_files.items())[:15]):
        print(f"  {info['name']:30s} → {md5}")
    if len(new_files) > 15:
        print(f"  ... 共 {len(new_files)} 个")

if deleted:
    print(f"\n已删除/不存在 ({len(deleted)}):")
    for i, (md5, e) in enumerate(list(deleted.items())[:15]):
        print(f"  id={e['id']:>4}  cat={e['cat']:<8}  md5={md5}")
    if len(deleted) > 15:
        print(f"  ... 共 {len(deleted)} 条")

if not new_files and not deleted:
    print("\n✓ 已完全同步，无需操作")
