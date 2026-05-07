const https = require('https');
const querystring = require('querystring');

// IMA API credentials
const CLIENT_ID = '6165e4d1fbbc58d18eb76b820f4bba97';
const API_KEY = 'eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtxc4aUHIL4J47sUJ9pz3Z1F3fIIHYml93JTTg==';

// Updated SYSTEM_CONFIG content with v12.2
const systemConfig = `【SYSTEM_CONFIG】v12.2
你正在操作 MSS（Meaning-Space Structure）理论体系。

核心公理（不可动摇）：
A1: 信息是本体论上首要的；物质/能量是其投影
A2: 0/1（二元判别）是意义的原子操作
A3: 1/0（自指崩溃）是封闭系统的奇点
A4: 封闭系统中逻辑熵总是增加
A5: 真矛盾不可能；表面矛盾信号需要维度提升
A6: 生命/心智是宇宙信息处理中的纠错子程序

操作规则：
- 永不声称完备性或终极性（RSCA合规）
- 每次响应标记置信度
- 不确定时声明边界而非编造
- 禁用术语：解决、终极、突破、超越、完美
- 使用替代：缓解、当前最佳理解、演化、投影、高保真

层级结构：
L1: 硬核公理（不可修改）
L2: 保护带理论（可调整）
L3: 启发式方法（可试验）
L4: 污染池（已拒绝内容）

当前版本: v12.2
历史版本: v3.1.0 → v12.2
更新日期: 2026-05-07
聚焦战场: 组织韧性 / AI对齐 / 文明诊断
`;

// Try to find and update the note
// IMA API endpoint (inferred from common patterns)
const API_HOST = 'ima.qq.com';
const API_PATH = '/api/v1/notes/search';

function makeRequest(path, method, data) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: API_HOST,
            port: 443,
            path: path,
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-Client-Id': CLIENT_ID,
                'X-Api-Key': API_KEY,
                'User-Agent': 'MSS-AI-Updater/1.0'
            }
        };

        const req = https.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(responseData);
                    resolve({ statusCode: res.statusCode, data: parsed });
                } catch (e) {
                    resolve({ statusCode: res.statusCode, data: responseData });
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

async function main() {
    console.log('IMA API Update Test');
    console.log('====================');
    
    try {
        // Step 1: Search for SYSTEM_CONFIG note
        console.log('\n1. Searching for SYSTEM_CONFIG note...');
        const searchResult = await makeRequest(
            '/api/v1/notes/search?q=SYSTEM_CONFIG',
            'GET'
        );
        console.log('Search result:', JSON.stringify(searchResult, null, 2));
        
        // If found, update it
        if (searchResult.data && searchResult.data.notes && searchResult.data.notes.length > 0) {
            const noteId = searchResult.data.notes[0].id;
            console.log(`\n2. Found note ID: ${noteId}`);
            console.log('3. Updating note content...');
            
            const updateResult = await makeRequest(
                `/api/v1/notes/${noteId}`,
                'PUT',
                {
                    title: '【SYSTEM_CONFIG】v12.2',
                    content: systemConfig,
                    tags: ['MSS', 'SYSTEM', 'v12.2']
                }
            );
            console.log('Update result:', JSON.stringify(updateResult, null, 2));
        } else {
            console.log('\n2. Note not found, creating new...');
            const createResult = await makeRequest(
                '/api/v1/notes',
                'POST',
                {
                    title: '【SYSTEM_CONFIG】v12.2',
                    content: systemConfig,
                    tags: ['MSS', 'SYSTEM', 'v12.2'],
                    knowledge_base: 'MSS理论体系归档'
                }
            );
            console.log('Create result:', JSON.stringify(createResult, null, 2));
        }
        
    } catch (error) {
        console.error('Error:', error.message);
        if (error.code === 'EPROTO') {
            console.error('\nSSL/TLS error - possible causes:');
            console.error('- Proxy interference');
            console.error('- Certificate validation issue');
            console.error('- Network configuration problem');
        }
    }
}

main();
