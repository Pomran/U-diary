"""
U-diary 照片上传工具
将 photos/ 文件夹中的照片批量上传到 Cloudflare R2
并生成 photos.json 数据文件

使用方法:
  1. 把照片放到 photos/ 文件夹
  2. 打开脚本填写你的 R2 配置
  3. 运行: python upload.py
"""

import os
import json
import mimetypes
import urllib.request
import urllib.error

# ═══════════════════════════════════
# 配置区 — 请填写你的 R2 信息
# ═══════════════════════════════════
ACCOUNT_ID = "你的 Account ID"      # 在 R2 页面右上角找到
ACCESS_KEY = "你的 Access Key ID"   # 在 R2 → 管理令牌 创建
SECRET_KEY = "你的 Secret Access Key"
BUCKET_NAME = "u-diary"
PUBLIC_URL = "https://pub-af6cc2aa40a64382b17825de8e4a74e0.r2.dev"  # 桶的公开访问域名
# ═══════════════════════════════════

PHOTOS_DIR = "photos"
OUTPUT_JSON = "photos.json"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}

def get_file_list():
    files = []
    if not os.path.isdir(PHOTOS_DIR):
        print(f"❌ 未找到 {PHOTOS_DIR}/ 文件夹")
        return files
    for f in sorted(os.listdir(PHOTOS_DIR)):
        ext = os.path.splitext(f)[1].lower()
        if ext in SUPPORTED_EXT:
            files.append(f)
    return files

def upload_file(filename):
    """使用 S3 兼容 API 上传文件到 R2"""
    filepath = os.path.join(PHOTOS_DIR, filename)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    # 使用 S3 API 上传
    import hmac
    import hashlib
    import datetime

    now = datetime.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    region = "auto"
    service = "s3"

    with open(filepath, "rb") as f:
        payload = f.read()

    payload_hash = hashlib.sha256(payload).hexdigest()

    # 构建 Canonical Request
    canonical_uri = f"/{filename}"
    canonical_querystring = ""
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    headers = {
        "Host": f"{BUCKET_NAME}.{ACCOUNT_ID}.r2.cloudflarestorage.com",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    canonical_headers = (
        f"host:{headers['Host']}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )

    canonical_request = (
        f"PUT\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    # 构建 StringToSign
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )

    # 计算签名
    def sign(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    date_key = sign(f"AWS4{SECRET_KEY}".encode(), date_stamp)
    region_key = sign(date_key, region)
    service_key = sign(region_key, service)
    signing_key = sign(service_key, "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"{algorithm} Credential={ACCESS_KEY}/{credential_scope},"
        f"SignedHeaders={signed_headers},Signature={signature}"
    )

    # 发送请求
    req = urllib.request.Request(
        url=f"https://{headers['Host']}/{filename}",
        data=payload,
        method="PUT",
        headers={
            "authorization": authorization,
            **headers,
            "Content-Type": content_type,
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status in (200, 204):
                return True
            else:
                print(f"  ← HTTP {resp.status}")
                return False
    except urllib.error.HTTPError as e:
        print(f"  ← HTTP {e.code}: {e.read().decode()[:200]}")
        return False

def generate_photos_json(files):
    """生成 photos.json 模板（你后续补标题和描述）"""
    db_path = os.path.join(os.path.dirname(__file__), OUTPUT_JSON)
    try:
        with open(db_path, encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    existing_ids = {p["id"] for p in existing}
    next_id = max(existing_ids) + 1 if existing_ids else 1

    cats = ["campus", "travel", "daily", "people", "night"]
    badges_list = ["memory", "sunny", "cloudy", "golden", "rainy", "warm", "cool", "vintage", "blur", "shadow"]

    new_entries = []
    for filename in files:
        photo_id = next_id
        next_id += 1
        # 检查是否已存在
        matched = [p for p in existing if p["src"].endswith(filename)]
        if matched:
            continue
        import random
        new_entries.append({
            "id": photo_id,
            "src": f"{PUBLIC_URL}/{filename}",
            "date": "20XX.XX.XX",
            "title": f"照片 {photo_id}",
            "desc": "在此填写照片背后的故事...",
            "cat": random.choice(cats),
            "badge": random.choice(badges_list),
        })

    if not new_entries:
        print("没有新照片需要添加")
        return

    existing.extend(new_entries)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"✅ photos.json 已更新，新增 {len(new_entries)} 条记录")
    print(f"⚠️  请手动编辑 photos.json 补全 title、date、desc 字段")

def main():
    files = get_file_list()
    if not files:
        print("❌ photos/ 文件夹为空，请先放入照片")
        return

    print(f"📸 发现 {len(files)} 张照片")
    print(f"📤 上传到 R2 存储桶: {BUCKET_NAME}")
    print()

    # 先上传
    success = 0
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] 上传 {f}...", end=" ")
        if upload_file(f):
            print("✅")
            success += 1
        else:
            print("❌")

    print(f"\n✅ 上传完成: {success}/{len(files)}")

    # 再生成 JSON
    if success:
        generate_photos_json(files)

if __name__ == "__main__":
    main()
