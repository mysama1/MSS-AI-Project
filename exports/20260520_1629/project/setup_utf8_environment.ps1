# MSS-AI Project UTF-8 环境配置脚本
# 解决 Windows 默认 GBK 编码导致的乱码问题

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MSS-AI UTF-8 环境配置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 设置当前 PowerShell 会话的编码
Write-Host "[1/4] 设置 PowerShell 输出编码为 UTF-8..." -ForegroundColor Yellow
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host "✓ PowerShell 编码已设置为 UTF-8" -ForegroundColor Green

# 2. 设置 Python 环境变量
Write-Host ""
Write-Host "[2/4] 配置 Python UTF-8 环境变量..." -ForegroundColor Yellow
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Write-Host "✓ PYTHONIOENCODING=utf-8 已设置" -ForegroundColor Green
Write-Host "✓ PYTHONUTF8=1 已设置" -ForegroundColor Green

# 3. 创建/更新 PowerShell Profile（持久化配置）
Write-Host ""
Write-Host "[3/4] 持久化配置到 PowerShell Profile..." -ForegroundColor Yellow

$profileContent = @'
# MSS-AI UTF-8 环境配置（自动加载）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# MSS-AI 项目快捷路径
function mss { Set-Location C:\MSS-AI-Project }
'@

if (!(Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "✓ 创建新的 PowerShell Profile" -ForegroundColor Green
}

# 检查是否已存在 MSS-AI 配置
$existingProfile = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($existingProfile -notmatch "MSS-AI UTF-8") {
    Add-Content -Path $PROFILE -Value "`n$profileContent"
    Write-Host "✓ UTF-8 配置已添加到 PowerShell Profile" -ForegroundColor Green
} else {
    Write-Host "✓ PowerShell Profile 已包含 UTF-8 配置" -ForegroundColor Green
}

# 4. 验证配置
Write-Host ""
Write-Host "[4/4] 验证配置..." -ForegroundColor Yellow

Write-Host ""
Write-Host "当前编码设置：" -ForegroundColor Cyan
Write-Host "  Console.OutputEncoding: $([Console]::OutputEncoding.EncodingName)"
Write-Host "  OutputEncoding: $($OutputEncoding.EncodingName)"
Write-Host "  PYTHONIOENCODING: $env:PYTHONIOENCODING"
Write-Host "  PYTHONUTF8: $env:PYTHONUTF8"

# 测试中文输出
Write-Host ""
Write-Host "中文测试：物理层是意义博弈的结算界面" -ForegroundColor Cyan

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "UTF-8 环境配置完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "说明：" -ForegroundColor Yellow
Write-Host "- 当前会话已生效" -ForegroundColor White
Write-Host "- 新打开的 PowerShell 窗口会自动加载 UTF-8 配置" -ForegroundColor White
Write-Host "- 使用 'mss' 命令可快速切换到 MSS-AI 项目目录" -ForegroundColor White
Write-Host ""
Write-Host "如需立即生效，请重新打开 PowerShell 窗口" -ForegroundColor Yellow
