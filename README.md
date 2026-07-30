# 晴れ日記 · U-diary

清新日记风格的大学照片分享站。

## 项目结构

```
U-diary/
├── index.html          # 主页面（无限滚动 + 分类筛选）
├── photos.json         # 照片元数据（标题、描述、分类等）
├── upload.py           # R2 批量上传脚本（放好照片后运行）
├── photos/             # 放你的照片原图（被 .gitignore 忽略）
├── .gitignore
└── README.md
```

## 使用流程

### 1. 上传照片到 R2

```bash
# 把照片放到 photos/ 文件夹
# 然后运行上传脚本
python upload.py
```

### 2. 更新 metadata

脚本运行后会生成 JSON 模板，手动编辑 `photos.json` 补全每张照片的：
- `title` — 标题
- `date` — 拍摄日期
- `desc` — 照片故事（一句话即可）
- `cat` — 分类（campus / travel / daily / people / night）
- `badge` — 标签关键词

### 3. 推送部署

```bash
git add photos.json
git commit -m "add: xxx张新照片"
git push
# → Cloudflare Pages 自动部署
```

## 技术栈

- 纯前端 HTML + CSS + JS，零依赖
- 照片托管在 Cloudflare R2
- 自动部署 via Cloudflare Pages + GitHub
