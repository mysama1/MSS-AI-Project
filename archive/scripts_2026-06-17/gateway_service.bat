@echo off
set QCLAW_CLI_NODE_BINARY=E:\QClaw\v0.2.26.557\resources\node\node.exe
set QCLAW_CLI_OPENCLAW_MJS=E:\QClaw\v0.2.26.557\resources\openclaw\node_modules\openclaw\openclaw.mjs
set QCLAW_LLM_BASE_URL=https://api.qclaw.ai/v1
set QCLAW_LLM_API_KEY=sk-c8552ade17df4b73ba4deabd3eb1af81
"%QCLAW_CLI_NODE_BINARY%" "%QCLAW_CLI_OPENCLAW_MJS%" gateway --port 50942 --allow-unconfigured
