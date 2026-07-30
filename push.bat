@echo off
chcp 65001 >nul
echo.
echo ================================
echo   U-diary 一键推送脚本
echo ================================
echo.

cd /d "%~dp0"

echo [1/4] 设置代理...
set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897
git config http.proxy http://127.0.0.1:7897
git config https.proxy http://127.0.0.1:7897

echo [2/4] 设置远程仓库...
git remote set-url origin https://github.com/Pomran/U-diary.git

echo [3/4] 切换到 main 分支...
git branch -M main

echo [4/4] 推送到 GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ✅ 推送成功！
    echo.
    echo 下一步: Cloudflare Pages 会自动部署
    echo 地址: https://ud.i-test.top
) else (
    echo.
    echo ❌ 推送失败，请检查网络连接后重试
    echo.
    echo 备选方案:
    echo 1. 打开 https://github.com/Pomran/U-diary
    echo 2. 手动上传文件即可
)

pause
