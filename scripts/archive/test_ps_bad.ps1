
$ErrorActionPreference = "Stop"
trap {{ Write-Error "MSS: 未处理异常 at $($_.InvocationInfo.ScriptLineNumber): $_" ; exit 1 }}


# BAD: POSIX commands in PS
ls -l C:/temp
rm -rf ./build
cd ~/Documents
cat file.txt | grep error
mkdir newdir
cp source.txt dest.txt
curl http://api.example.com/data
echo Done

# OK: These are native PS
Get-ChildItem C:/temp
Remove-Item -Recurse -Force ./build
Write-Output Done
