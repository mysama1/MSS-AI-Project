# MSS-AI Project Cleanup Report

Generated: 2026-05-21T03:19:54.539587

## Summary

- Files Processed: 241
- Issues Fixed: 202
- Sensitive Data Findings: 14

## Sensitive Data Scan

| File | Type | Line | Context |
|------|------|------|---------|
| ARCHITECTURE.md | IP Address | 191 | 0.0.0.0 |
| ARCHITECTURE.md | IP Address | 200 | 0.0.0.0 |
| batch_import_historical.py | API Key | 15 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| docker-compose.yml | IP Address | 10 | 0.0.0.0 |
| import_all_historical.py | API Key | 13 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| import_by_file.py | API Key | 15 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| import_ima_v2.py | API Key | 16 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| import_organized.py | API Key | 13 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| import_to_ima.py | API Key | 16 | API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |
| README.md | Email | 231 | research@mss-ai.org |
| setup.py | Email | 31 | research@mss-ai.org |
| websocket_server.py | IP Address | 344 | 0.0.0.0 |
| web_api.py | IP Address | 442 | 0.0.0.0 |
| scripts\ima_update.js | API Key | 6 | API_KEY = 'eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtx... |

## Documentation Status

| Document | Exists | Size |
|----------|--------|------|
| README.md | ✅ | 8624 bytes |
| LICENSE | ❌ | N/A |
| CONTRIBUTING.md | ❌ | N/A |
| CODE_OF_CONDUCT.md | ❌ | N/A |
| docs/ | ✅ | 0 bytes |
