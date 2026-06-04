# IMA API Update Script v2
# Uses correct endpoints from ima-skill documentation

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
if ($useUtf8Bytes) {
    Write-Host "PowerShell 5.1 detected, using UTF-8 byte array mode"
}

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

Write-Host "IMA API Update v2"
Write-Host "=================="

# Step 1: Search for SYSTEM_CONFIG note
Write-Host ""
Write-Host "1. Searching for SYSTEM_CONFIG note..."
try {
    $searchBody = @{
        search_type = 0
        query_info = @{ title = "SYSTEM_CONFIG" }
        start = 0
        end = 20
    }
    
    $searchResult = Invoke-ImaApi "openapi/note/v1/search_note_book" $searchBody
    
    if ($searchResult.docs -and $searchResult.docs.Count -gt 0) {
        $doc = $searchResult.docs[0].doc.basic_info
        $docId = $doc.docid
        $title = $doc.title
        
        Write-Host "   Found: $title (ID: $docId)"
        
        # Step 2: Append version update notice
        Write-Host ""
        Write-Host "2. Appending version update to note..."
        
        $appendContent = "`n`n---`n`n[版本更新 2026-05-07]`n当前系统版本: v12.2`n本条目原始版本: v3.1.0`n更新内容: 版本号同步，公理内容无变更`n"
        
        $appendBody = @{
            doc_id = $docId
            content_format = 1
            content = $appendContent
        }
        
        $appendResult = Invoke-ImaApi "openapi/note/v1/append_doc" $appendBody
        Write-Host "   Successfully appended version update"
        Write-Host "   Doc ID: $($appendResult.doc_id)"
        
    } else {
        Write-Host "   SYSTEM_CONFIG not found in notes"
    }
    
    Write-Host ""
    Write-Host "IMA update completed"
    
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
