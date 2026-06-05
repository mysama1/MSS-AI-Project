/**
 * MSS VDP VS Code Extension
 * Real-time code quality scanning with 10 languages, 50+ rules.
 * 
 * Features:
 *   - Auto-scan on save
 *   - Status bar violation count (clickable)
 *   - Problems panel diagnostics
 *   - Multi-language support
 */

const vscode = require('vscode');
const http = require('http');
const path = require('path');

// ── Language detection ──

const EXT_TO_LANG = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.rs': 'rust',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.kt': 'kotlin',
    '.cs': 'csharp',
};

const LANG_TO_ENDPOINT = {
    'python': '/vdp/scan/python',
    'javascript': '/vdp/scan/javascript',
    'typescript': '/vdp/scan/typescript',
    'rust': '/vdp/scan/rust',
    'java': '/vdp/scan/java',
    'cpp': '/vdp/scan/cpp',
    'c': '/vdp/scan/c',
    'go': '/vdp/scan/go',
    'ruby': '/vdp/scan/ruby',
    'php': '/vdp/scan/php',
    'kotlin': '/vdp/scan/kotlin',
    'csharp': '/vdp/scan/csharp',
};

// ── Global state ──

let statusBarItem = null;
let diagnosticCollection = null;
let scanCount = 0;
let lastViolationCount = 0;

// ── API Client ──

function vdpRequest(endpoint, code) {
    return new Promise((resolve, reject) => {
        const config = vscode.workspace.getConfiguration('vdp');
        const apiUrl = config.get('apiUrl', 'http://127.0.0.1:53000');
        const url = new URL(endpoint, apiUrl);
        
        const postData = JSON.stringify({
            code: code,
            format: 'json',
            strictness: 0.7,
        });
        
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 10000,
        };
        
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch {
                    // Not JSON — try plain text response
                    resolve({ raw: data, violations: [] });
                }
            });
        });
        
        req.on('error', (e) => {
            reject(new Error(`VDP API unreachable: ${e.message}\nIs the VDP server running? py -3.11 skill_api.py 53000`));
        });
        
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('VDP API timeout'));
        });
        
        req.write(postData);
        req.end();
    });
}

// ── Diagnostics ──

function violationsToDiagnostics(violations, document) {
    const diags = [];
    const minSeverity = vscode.workspace.getConfiguration('vdp').get('minSeverity', 'warn');
    const severityMap = {
        'critical': vscode.DiagnosticSeverity.Error,
        'error': vscode.DiagnosticSeverity.Error,
        'warn': vscode.DiagnosticSeverity.Warning,
        'info': vscode.DiagnosticSeverity.Information,
        'hint': vscode.DiagnosticSeverity.Hint,
    };
    
    const severityOrder = { critical: 0, error: 1, warn: 2, info: 3, hint: 4 };
    const minOrder = severityOrder[minSeverity] ?? 2;
    
    for (const v of (violations || [])) {
        if (severityOrder[v.severity] > minOrder) continue;
        
        const line = Math.max(0, (v.line || 1) - 1);
        const col = Math.max(0, (v.column || 1) - 1);
        const endCol = Math.min((document.lineAt(line)?.text?.length || 80), col + 80);
        
        const range = new vscode.Range(line, col, line, endCol);
        const severity = severityMap[v.severity] || vscode.DiagnosticSeverity.Warning;
        
        const diag = new vscode.Diagnostic(
            range,
            `[${v.rule || 'VDP'}] ${v.message || v.description || 'Unknown violation'}`,
            severity
        );
        diag.source = `VDP:${v.rule || ''}`;
        diag.code = v.rule || '';
        diags.push(diag);
    }
    
    return diags;
}

// ── Core: Scan File ──

async function scanDocument(document) {
    if (!document || document.isUntitled) return;
    
    const ext = path.extname(document.fileName).toLowerCase();
    const lang = EXT_TO_LANG[ext];
    if (!lang) return;
    
    const endpoint = LANG_TO_ENDPOINT[lang];
    if (!endpoint) return;
    
    try {
        const result = await vdpRequest(endpoint, document.getText());
        const violations = result.violations || result.results || result.errors || [];
        scanCount++;
        lastViolationCount = violations.length;
        
        // Update diagnostics
        const diags = violationsToDiagnostics(violations, document);
        diagnosticCollection.set(document.uri, diags);
        
        // Update status bar
        updateStatusBar();
        
        return { violations: violations.length, diags: diags.length };
    } catch (e) {
        // API error — clear old diagnostics, show warning
        diagnosticCollection.delete(document.uri);
        lastViolationCount = -1;
        updateStatusBar();
        return { error: e.message };
    }
}

async function scanAllDocuments() {
    const docs = vscode.workspace.textDocuments.filter(d => !d.isUntitled);
    let total = 0;
    
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'VDP: Scanning all open files...',
        cancellable: true,
    }, async (progress) => {
        for (let i = 0; i < docs.length; i++) {
            const r = await scanDocument(docs[i]);
            if (r && r.violations !== undefined) total += r.violations;
            progress.report({ increment: 100 / docs.length });
        }
    });
    
    vscode.window.showInformationMessage(`VDP: Scanned ${docs.length} files, ${total} violations found`);
}

// ── Scan all workspace files (not just open ones) ──

async function scanWorkspaceFiles() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        const editor = vscode.window.activeTextEditor;
        if (editor) await scanDocument(editor.document).catch(() => {});
        return;
    }
    
    const scanExts = Object.keys(EXT_TO_LANG);
    let files = [];
    
    for (const folder of workspaceFolders) {
        const pattern = `**/*{${scanExts.join(',')}}`;
        const found = await vscode.workspace.findFiles(
            new vscode.RelativePattern(folder, pattern),
            '**/node_modules/**,**/.git/**,**/__pycache__/**'
        );
        files.push(...found);
    }
    
    if (files.length === 0) return;
    files = files.slice(0, 50);
    
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Window,
        title: `VDP: Scanning ${files.length} workspace files...`,
    }, async (progress) => {
        let total = 0;
        for (let i = 0; i < files.length; i++) {
            try {
                const doc = await vscode.workspace.openTextDocument(files[i]);
                const r = await scanDocument(doc);
                if (r && r.violations !== undefined) total += r.violations;
            } catch {}
            progress.report({ increment: 100 / files.length });
        }
        const msg = total === 0 ? '$(pass) VDP: Workspace clean' : `$(warning) VDP: ${total} violations`;
        vscode.window.setStatusBarMessage(msg, 8000);
    });
}

// ── Status Bar ──

function updateStatusBar(autoScanEnabled = null) {
    if (!statusBarItem) return;
    
    if (autoScanEnabled === null) {
        autoScanEnabled = vscode.workspace.getConfiguration('vdp').get('autoScanOnSave', true);
    }
    
    if (lastViolationCount < 0) {
        statusBarItem.text = `$(error) VDP: OFF`;
        statusBarItem.tooltip = 'VDP API unreachable. Check if server is running.';
        statusBarItem.backgroundColor = undefined;
    } else if (lastViolationCount === 0) {
        statusBarItem.text = `$(pass) VDP: 0`;
        statusBarItem.tooltip = `VDP: All clear (${scanCount} scans)`;
        statusBarItem.backgroundColor = undefined;
    } else {
        statusBarItem.text = `$(warning) VDP: ${lastViolationCount}`;
        statusBarItem.tooltip = `VDP: ${lastViolationCount} violations (${scanCount} scans)`;
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }
    
    statusBarItem.show();
}

// ── Activation ──

function activate(context) {
    console.log('MSS VDP extension activated');
    
    // Diagnostic collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection('vdp');
    context.subscriptions.push(diagnosticCollection);
    
    // Status bar
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'vdp.scan';
    statusBarItem.tooltip = 'VDP: Scan current file';
    context.subscriptions.push(statusBarItem);
    
    const showStatusBar = vscode.workspace.getConfiguration('vdp').get('showStatusBar', true);
    if (showStatusBar) {
        updateStatusBar();
    }
    
    // ── Commands ──
    
    context.subscriptions.push(
        vscode.commands.registerCommand('vdp.scan', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }
            const r = await scanDocument(editor.document);
            if (r && r.error) {
                vscode.window.showErrorMessage(`VDP: ${r.error}`);
            } else if (r) {
                const msg = r.violations === 0 
                    ? 'VDP: Clear — 0 violations ✅' 
                    : `VDP: ${r.violations} violations (${r.diags} shown)`;
                vscode.window.showInformationMessage(msg);
            }
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('vdp.scanAll', scanAllDocuments)
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('vdp.dashboard', () => {
            const panel = vscode.window.createWebviewPanel(
                'vdpDashboard',
                'VDP Dashboard',
                vscode.ViewColumn.Beside,
                { enableScripts: true }
            );
            panel.webview.html = getDashboardHtml();
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('vdp.toggleAutoScan', async () => {
            const config = vscode.workspace.getConfiguration('vdp');
            const current = config.get('autoScanOnSave', true);
            await config.update('autoScanOnSave', !current, true);
            updateStatusBar(!current);
            vscode.window.showInformationMessage(`VDP: Auto-scan ${!current ? 'ENABLED' : 'DISABLED'}`);
        })
    );
    
    // ── Auto-scan triggers: activate, change (debounced), save, editor switch ──
    let scanTimeout = null;
    
    // On document change: debounced 2s (scan without needing save)
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(async (event) => {
            const autoScan = vscode.workspace.getConfiguration('vdp').get('autoScanOnSave', true);
            if (!autoScan || !event.document || event.document.isUntitled) return;
            if (scanTimeout) clearTimeout(scanTimeout);
            scanTimeout = setTimeout(() => scanDocument(event.document).catch(() => {}), 2000);
        })
    );
    
    // On save: immediate scan
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (vscode.workspace.getConfiguration('vdp').get('autoScanOnSave', true)) {
                await scanDocument(document);
            }
        })
    );
    
    // On editor switch: scan newly focused file
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(async (editor) => {
            if (editor && !editor.document.isUntitled) {
                await scanDocument(editor.document).catch(() => {});
            }
        })
    );
    
    // On activation: scan all workspace files
    scanWorkspaceFiles().catch(() => {});
    }
    
    // ── Config change ──
    
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('vdp.showStatusBar')) {
                const show = vscode.workspace.getConfiguration('vdp').get('showStatusBar', true);
                if (show) {
                    updateStatusBar();
                } else {
                    statusBarItem.hide();
                }
            }
            if (e.affectsConfiguration('vdp.minSeverity')) {
                // Re-scan to update diagnostic severity
                if (editor) scanDocument(editor.document).catch(() => {});
            }
        })
    );
}

// ── Dashboard HTML ──

function getDashboardHtml() {
    return `<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MSS VDP Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: var(--vscode-font-family, 'Consolas', monospace);
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            padding: 20px;
        }
        h1 { font-size: 1.5em; margin-bottom: 5px; color: var(--vscode-textLink-foreground, #007acc); }
        .subtitle { color: var(--vscode-descriptionForeground); margin-bottom: 20px; }
        .card {
            background: var(--vscode-editor-inactiveSelectionBackground);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .card h2 { font-size: 1.1em; margin-bottom: 10px; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
        .stat { 
            background: var(--vscode-badge-background, #333);
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }
        .stat .value { font-size: 2em; font-weight: bold; color: var(--vscode-charts-green, #89d185); }
        .stat .value.warn { color: var(--vscode-charts-orange, #d1865e); }
        .stat .value.err { color: var(--vscode-errorForeground, #f44747); }
        .stat .label { font-size: 0.8em; color: var(--vscode-descriptionForeground); margin-top: 4px; }
        .lang-grid { display: flex; flex-wrap: wrap; gap: 6px; }
        .lang-tag {
            background: var(--vscode-badge-background);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
        }
        .rules { font-size: 0.9em; line-height: 1.8; }
        .rule { padding: 2px 6px; border-radius: 4px; margin: 2px 0; }
        .rule.c { background: rgba(244,71,71,0.15); } /* critical */
        .rule.e { background: rgba(244,71,71,0.08); } /* error */
        .rule.w { background: rgba(209,134,94,0.08); }  /* warning */
        button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 8px;
            margin-top: 12px;
        }
        button:hover { background: var(--vscode-button-hoverBackground); }
    </style>
</head>
<body>
    <h1>🔍 MSS VDP Dashboard</h1>
    <p class="subtitle">Verification Discipline Protocol — 10 languages, 50+ rules</p>

    <div class="card">
        <h2>📊 Current Session</h2>
        <div class="stat-grid">
            <div class="stat">
                <div class="value" id="scans">0</div>
                <div class="label">Scans Completed</div>
            </div>
            <div class="stat">
                <div class="value" id="violations">0</div>
                <div class="label">Last Violations</div>
            </div>
            <div class="stat">
                <div class="value" id="files">0</div>
                <div class="label">Open Files</div>
            </div>
            <div class="stat">
                <div class="value" id="api">⏳</div>
                <div class="label">API Status</div>
            </div>
        </div>
        <button onclick="refresh()">🔄 Refresh</button>
        <button onclick="scanAll()">🔍 Scan All Files</button>
    </div>

    <div class="card">
        <h2>🌐 Supported Languages</h2>
        <div class="lang-grid" id="langs">
            <span class="lang-tag">Python</span>
            <span class="lang-tag">JavaScript</span>
            <span class="lang-tag">TypeScript</span>
            <span class="lang-tag">Rust</span>
            <span class="lang-tag">Java</span>
            <span class="lang-tag">C/C++</span>
            <span class="lang-tag">Go</span>
            <span class="lang-tag">Ruby</span>
            <span class="lang-tag">PHP</span>
            <span class="lang-tag">Kotlin</span>
            <span class="lang-tag">C#</span>
        </div>
    </div>

    <div class="card">
        <h2>📐 Rule Categories (50+)</h2>
        <div class="rules">
            <div class="rule c">🔴 V1_PATH: Path existence validation before file operations</div>
            <div class="rule e">🟠 V2_ERROR: Direct error code reporting, no attribution guessing</div>
            <div class="rule e">🟠 V3_ENCODING: Explicit -Encoding UTF8 for CJK I/O</div>
            <div class="rule w">🟡 V4_ATOMIC: Atomic idempotent operations (backup before write)</div>
            <div class="rule w">🟡 V5_TIMEOUT: Timeout → degradation after 2 retries</div>
            <div class="rule e">🟠 V6_FACT: Fact/Inference separation with evidence anchors</div>
            <div class="rule c">🔴 V7_PSEUDO: Pseudo-constraint detection (system→user leakage)</div>
            <div class="rule w">🟡 V8_LEAK: Memory leak / stale resource detection</div>
            <div class="rule w">🟡 V9_ASYNC: Unhandled promise rejection / async trap</div>
            <div class="rule e">🟠 V10_NULL: Null safety / undefined access</div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        function refresh() { vscode.postMessage({ command: 'refresh' }); }
        function scanAll() { vscode.postMessage({ command: 'scanAll' }); }
        
        window.addEventListener('message', event => {
            const msg = event.data;
            if (msg.scans) document.getElementById('scans').textContent = msg.scans;
            if (msg.violations !== undefined) {
                const el = document.getElementById('violations');
                el.textContent = msg.violations;
                el.className = msg.violations > 5 ? 'value err' : msg.violations > 0 ? 'value warn' : 'value';
            }
            if (msg.files) document.getElementById('files').textContent = msg.files;
            if (msg.api) document.getElementById('api').textContent = msg.api ? '✅' : '❌';
        });
        
        // Initial data
        refresh();
    </script>
</body>
</html>`;
}

// ── Deactivation ──

function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

module.exports = { activate, deactivate };
