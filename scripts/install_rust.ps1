# Track A: Rust VDP 加速器 Phase 1 安装脚本
# 下载 rustup-init.exe 并静默安装 Rust 工具链到 E:\Rust (避开 C 盘)

$ErrorActionPreference = "Stop"

Write-Host "=== Downloading rustup-init ==="
$rustupUrl = "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
$rustupExe = "$env:TEMP\rustup-init.exe"
Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupExe -UseBasicParsing

Write-Host "=== Installing Rust to E:\Rust ==="
$env:CARGO_HOME = "E:\Rust\.cargo"
$env:RUSTUP_HOME = "E:\Rust\.rustup"

& $rustupExe -y --default-toolchain stable --no-modify-path `
    --component rust-analyzer,clippy `
    --profile minimal

Remove-Item $rustupExe -Force -ErrorAction SilentlyContinue

Write-Host "=== Refreshing PATH ==="
$env:Path = "E:\Rust\.cargo\bin;$env:Path"
rustc --version
cargo --version
Write-Host "=== Rust installed successfully ==="
