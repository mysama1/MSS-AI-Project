# Verify IMA SYSTEM_CONFIG note content

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

Write-Host "IMA SYSTEM_CONFIG Verification"
Write-Host "==============================="

# Target note ID
$docId = "7458136705231089"

# Get full content
Write-Host ""
Write-Host "Reading full content..."
try {
    $contentBody = @{
        doc_id = $docId
        target_content_format = 0
    }
    
    $contentResult = Invoke-ImaApi "openapi/note/v1/get_doc_content" $contentBody
    
    if ($contentResult.data) {
        $content = $contentResult.data.content
        
        # Check for version info
        $hasV12_2 = $content -like "*v12.2*"
        $hasV3_1 = $content -like "*v3.1*"
        $hasUpdate = $content -like "*版本更新*"
        
        Write-Host ""
        Write-Host "Version check:"
        Write-Host "  Contains v12.2: $hasV12_2"
        Write-Host "  Contains v3.1: $hasV3_1"
        Write-Host "  Contains 版本更新: $hasUpdate"
        
        # Show relevant lines
        Write-Host ""
        Write-Host "Content lines containing version info:"
        $lines = $content -split "`n"
        foreach ($line in $lines) {
            if ($line -like "*v12.2*" -or $line -like "*v3.1*" -or $line -like "*版本*" -or $line -like "*更新*") {
                Write-Host "  $line"
            }
        }
        
        Write-Host ""
        Write-Host "Full content length: $($content.Length) chars"
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
