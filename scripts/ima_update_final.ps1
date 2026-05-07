# Update IMA SYSTEM_CONFIG note with v12.2 version info

$ErrorActionPreference = "Stop"

# User provided credentials
$CLIENT_ID = '6165e4d1fbbc58d18eb76b820f4bba97'
$API_KEY = 'eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtxc4aUHIL4J47sUJ9pz3Z1F3fIIHYml93JTTg=='

$headers = @{
    "ima-openapi-clientid" = $CLIENT_ID
    "ima-openapi-apikey"   = $API_KEY
    "Content-Type"         = "application/json; charset=utf-8"
}

$baseUrl = "https://ima.qq.com"

# PowerShell 5.1 UTF-8 fix
$useUtf8Bytes = $PSVersionTable.PSVersion.Major -le 5

function Invoke-ImaApi($path, $body) {
    $url = "$baseUrl/$path"
    $jsonBody = $body | ConvertTo-Json -Depth 10 -Compress
    
    if ($useUtf8Bytes) {
        $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $utf8Bytes -ContentType "application/json; charset=utf-8" -Headers $headers
    } else {
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $jsonBody -ContentType "application/json; charset=utf-8" -Headers $headers
    }
    
    return $response
}

Write-Host "IMA SYSTEM_CONFIG Update"
Write-Host "========================"

# Target note ID
$docId = "7458136705231089"

# Step 1: Get current content
Write-Host ""
Write-Host "1. Reading current content..."
try {
    $contentBody = @{
        doc_id = $docId
        target_content_format = 0
    }
    
    $contentResult = Invoke-ImaApi "openapi/note/v1/get_doc_content" $contentBody
    
    if ($contentResult.data) {
        $currentContent = $contentResult.data.content
        Write-Host "   Current content length: $($currentContent.Length) chars"
        Write-Host "   First 200 chars: $($currentContent.Substring(0, [Math]::Min(200, $currentContent.Length)))"
        
        # Check if already updated
        if ($currentContent -like "*v12.2*") {
            Write-Host ""
            Write-Host "   Note already contains v12.2 - skipping update"
        } else {
            # Step 2: Append version update
            Write-Host ""
            Write-Host "2. Appending v12.2 version update..."
            
            $appendContent = @"

---

[版本更新 2026-05-07]
当前系统版本: v12.2
本条目原始版本: v3.1.0
更新内容: 版本号同步，公理内容无变更
更新者: QClaw Arbitration System
"@
            
            $appendBody = @{
                doc_id = $docId
                content_format = 1
                content = $appendContent
            }
            
            $appendResult = Invoke-ImaApi "openapi/note/v1/append_doc" $appendBody
            
            Write-Host "   Successfully appended version update"
            Write-Host "   Doc ID: $($appendResult.data.doc_id)"
        }
    } else {
        Write-Host "   No content found in response"
        Write-Host "   Response: $($contentResult | ConvertTo-Json -Depth 3)"
    }
    
    Write-Host ""
    Write-Host "Update completed successfully"
    
} catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)"
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $errorBody = $reader.ReadToEnd()
        Write-Host "API Error: $errorBody" -ForegroundColor Red
    }
}
