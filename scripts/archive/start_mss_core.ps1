# MSS-AI 核心推理服务启动脚本
# 使用方法: .\start_mss_core.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== MSS-AI Core Server 启动 ===" -ForegroundColor Cyan

# 检查 Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 未安装或不在 PATH 中"
    exit 1
}

# 检查依赖
$deps = @("fastapi", "uvicorn", "requests", "pydantic")
foreach ($dep in $deps) {
    $installed = pip show $dep 2>$null
    if (-not $installed) {
        Write-Host "安装依赖: $dep" -ForegroundColor Yellow
        pip install $dep
    }
}

# 检查 Ollama
Write-Host "检查 Ollama 服务..." -ForegroundColor Yellow
try {
    $ollama = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    Write-Host "Ollama 服务正常，模型数量: $($ollama.models.Count)" -ForegroundColor Green
} catch {
    Write-Error "Ollama 服务未运行，请先启动 ollama serve"
    exit 1
}

# 检查 MSS-AI 模型
$mssModel = $ollama.models | Where-Object { $_.name -like "mss-ai*" }
if (-not $mssModel) {
    Write-Warning "未找到 MSS-AI 模型，请先拉取: ollama pull mss-ai-v3_6:latest"
} else {
    Write-Host "MSS-AI 模型: $($mssModel.name)" -ForegroundColor Green
}

# 启动服务
Write-Host "`n启动 MSS-AI Core Server (端口 8000)..." -ForegroundColor Cyan
Write-Host "接口列表:" -ForegroundColor Yellow
Write-Host "  POST http://127.0.0.1:8000/v1/reason   - 核心推理"
Write-Host "  POST http://127.0.0.1:8000/v1/verify   - 命题验证"
Write-Host "  POST http://127.0.0.1:8000/v1/infer    - 模式推导"
Write-Host "  GET  http://127.0.0.1:8000/health      - 健康检查"
Write-Host ""

Set-Location "E:\AI_Workspace\MSS-AI\project"
python -m uvicorn mss_core_server:app --host 127.0.0.1 --port 8000 --reload
