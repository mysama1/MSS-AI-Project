# Search IMA Knowledge Base for SYSTEM_CONFIG

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

Write-Host "IMA Knowledge Base Search"
Write-Host "========================="

# Step 1: List all knowledge bases
Write-Host ""
Write-Host "1. Listing all knowledge bases..."
try {
    $kbBody = @{
        query = ""
        cursor = ""
        limit = 20
    }
    
    $kbResult = Invoke-ImaApi "openapi/wiki/v1/search_knowledge_base" $kbBody
    
    if ($kbResult.data -and $kbResult.data.knowledge_base_list) {
        Write-Host "   Found $($kbResult.data.knowledge_base_list.Count) knowledge bases:"
        foreach ($kb in $kbResult.data.knowledge_base_list) {
            $info = $kb.knowledge_base_info
            Write-Host "   - $($info.name) (ID: $($info.id))"
        }
        
        # Look for MSS knowledge base
        $mssKb = $kbResult.data.knowledge_base_list | Where-Object { 
            $_.knowledge_base_info.name -like "*MSS*" -or 
            $_.knowledge_base_info.name -like "*mss*" 
        }
        
        if ($mssKb) {
            $mssKbId = $mssKb[0].knowledge_base_info.id
            $mssKbName = $mssKb[0].knowledge_base_info.name
            Write-Host ""
            Write-Host "2. Found MSS KB: $mssKbName (ID: $mssKbId)"
            
            # Step 2: Search for SYSTEM_CONFIG in this KB
            Write-Host ""
            Write-Host "3. Searching for SYSTEM_CONFIG in KB..."
            $searchBody = @{
                query = "SYSTEM_CONFIG"
                knowledge_base_id = $mssKbId
                cursor = ""
            }
            
            $searchResult = Invoke-ImaApi "openapi/wiki/v1/search_knowledge" $searchBody
            
            if ($searchResult.data -and $searchResult.data.info_list) {
                Write-Host "   Found $($searchResult.data.info_list.Count) results:"
                foreach ($item in $searchResult.data.info_list) {
                    Write-Host "   - $($item.title) (Type: $($item.media_type))"
                }
            } else {
                Write-Host "   No results found"
            }
            
            # Step 3: List all content in KB
            Write-Host ""
            Write-Host "4. Listing all content in KB..."
            $listBody = @{
                knowledge_base_id = $mssKbId
                cursor = ""
                limit = 50
            }
            
            $listResult = Invoke-ImaApi "openapi/wiki/v1/get_knowledge_list" $listBody
            
            if ($listResult.data -and $listResult.data.knowledge_list) {
                Write-Host "   Found $($listResult.data.knowledge_list.Count) items:"
                foreach ($item in $listResult.data.knowledge_list) {
                    $type = if ($item.folder_id) { "Folder" } else { "File" }
                    Write-Host "   - [$type] $($item.title)"
                }
            }
        } else {
            Write-Host "   No MSS knowledge base found"
        }
    } else {
        Write-Host "   No knowledge bases found"
    }
    
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
