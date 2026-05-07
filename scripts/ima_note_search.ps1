# Search IMA Notes for SYSTEM_CONFIG

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

Write-Host "IMA Note Search"
Write-Host "==============="

# Step 1: Search notes by title
Write-Host ""
Write-Host "1. Searching notes by title 'SYSTEM_CONFIG'..."
try {
    $searchBody = @{
        search_type = 0
        query_info = @{ title = "SYSTEM_CONFIG" }
        start = 0
        end = 20
    }
    
    $searchResult = Invoke-ImaApi "openapi/note/v1/search_note_book" $searchBody
    
    Write-Host "   Response structure:"
    Write-Host "   - retcode: $($searchResult.retcode)"
    Write-Host "   - errmsg: $($searchResult.errmsg)"
    
    if ($searchResult.data) {
        Write-Host "   - data type: $($searchResult.data.GetType().Name)"
        
        if ($searchResult.data.docs) {
            Write-Host "   - docs count: $($searchResult.data.docs.Count)"
            
            if ($searchResult.data.docs.Count -gt 0) {
                foreach ($doc in $searchResult.data.docs) {
                    $basicInfo = $doc.doc.basic_info
                    Write-Host "   Found: $($basicInfo.title) (ID: $($basicInfo.docid))"
                }
            } else {
                Write-Host "   No docs found"
            }
        } else {
            Write-Host "   No docs field in data"
            Write-Host "   Data content: $($searchResult.data | ConvertTo-Json -Depth 3)"
        }
    } else {
        Write-Host "   No data field in response"
    }
    
    # Step 2: Search with broader term
    Write-Host ""
    Write-Host "2. Searching notes by title 'MSS'..."
    $searchBody2 = @{
        search_type = 0
        query_info = @{ title = "MSS" }
        start = 0
        end = 20
    }
    
    $searchResult2 = Invoke-ImaApi "openapi/note/v1/search_note_book" $searchBody2
    
    if ($searchResult2.data -and $searchResult2.data.docs) {
        Write-Host "   Found $($searchResult2.data.docs.Count) notes with 'MSS' in title"
        foreach ($doc in $searchResult2.data.docs) {
            $basicInfo = $doc.doc.basic_info
            Write-Host "   - $($basicInfo.title) (ID: $($basicInfo.docid))"
        }
    } else {
        Write-Host "   No notes found with 'MSS' in title"
    }
    
    # Step 3: List all notebooks
    Write-Host ""
    Write-Host "3. Listing all notebooks..."
    $folderBody = @{
        cursor = "0"
        limit = 20
    }
    
    $folderResult = Invoke-ImaApi "openapi/note/v1/list_note_folder_by_cursor" $folderBody
    
    if ($folderResult.data -and $folderResult.data.note_book_folders) {
        Write-Host "   Found $($folderResult.data.note_book_folders.Count) notebooks:"
        foreach ($folder in $folderResult.data.note_book_folders) {
            $info = $folder.folder.basic_info
            Write-Host "   - $($info.name) (ID: $($info.folder_id), Notes: $($info.note_number))"
        }
        
        # Step 4: List notes in each notebook
        foreach ($folder in $folderResult.data.note_book_folders) {
            $folderId = $folder.folder.basic_info.folder_id
            $folderName = $folder.folder.basic_info.name
            
            Write-Host ""
            Write-Host "4. Listing notes in '$folderName'..."
            
            $noteBody = @{
                folder_id = $folderId
                cursor = ""
                limit = 20
            }
            
            $noteResult = Invoke-ImaApi "openapi/note/v1/list_note_by_folder_id" $noteBody
            
            if ($noteResult.data -and $noteResult.data.note_book_list) {
                foreach ($note in $noteResult.data.note_book_list) {
                    $info = $note.basic_info.basic_info
                    Write-Host "   - $($info.title) (ID: $($info.docid))"
                }
            }
        }
    } else {
        Write-Host "   No notebooks found"
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
