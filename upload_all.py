"""U-diary 批量上传照片到 R2 (跳过已存在的)"""
import os
import json
import subprocess
import re

TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
PHOTOS_DIR = r"C:\Users\liu\Desktop\photo-diary\photos"
JSON_PATH = r"C:\Users\liu\Desktop\photo-diary\photos.json"
BUCKET = "u-diary"
WRANGLER = r"C:\Users\liu\AppData\Roaming\npm\wrangler.cmd"

env = os.environ.copy()
env["CLOUDFLARE_API_TOKEN"] = TOKEN
env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
env["HTTP_PROXY"] = "http://127.0.0.1:7897"

EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

def get_uploaded_files():
    try:
        with open(JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {p["src"].split("/")[-1] for p in data}
    except Exception:
        return set()

def upload(fname):
    filepath = os.path.join(PHOTOS_DIR, fname)
    result = subprocess.run(
        [WRANGLER, "r2", "object", "put", f"{BUCKET}/{fname}",
         f"--file={filepath}", "--remote"],
        capture_output=True, text=True, env=env, timeout=300,
        encoding="utf-8", errors="replace"
    )
    return result.returncode == 0, (result.stderr or result.stdout)[-150:]

def main():
    files = sorted(
        f for f in os.listdir(PHOTOS_DIR)
        if os.path.splitext(f)[1].lower() in EXT
    )
    uploaded_already = get_uploaded_files()
    todo = [f for f in files if f not in uploaded_already]

    if not todo:
        print(f"没有新照片需要上传 (共 {len(files)} 张，全部已上传)")
        return

    print(f"共 {len(files)} 张，已上传 {len(files)-len(todo)}，待上传 {len(todo)} 张")

    ok, failed = [], []
    for i, fname in enumerate(todo, 1):
        size_mb = os.path.getsize(os.path.join(PHOTOS_DIR, fname)) / 1048576
        print(f"[{i}/{len(todo)}] {fname} ({size_mb:.1f}MB)...", end=" ", flush=True)
        success, err = upload(fname)
        if success:
            print("OK")
            ok.append(fname)
        else:
            print(f"FAIL: {err}")
            failed.append(fname)

    print(f"\n结果: 上传成功 {len(ok)}，失败 {len(failed)}")
    if failed:
        print("失败文件:")
        for f in failed:
            print(f"  {f}")

if __name__ == "__main__":
    main()
