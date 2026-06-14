$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://127.0.0.1:5173"
$node = "C:\Users\asdfm\.codex\runtimes\node-v24.15.0-win-x64\node.exe"
$npmCli = "C:\Users\asdfm\.codex\runtimes\node-v24.15.0-win-x64\node_modules\npm\bin\npm-cli.js"

Set-Location $appDir

if (-not (Test-Path (Join-Path $appDir "node_modules"))) {
    & $node $npmCli install
}

$listening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    Start-Process -FilePath $node `
        -ArgumentList @($npmCli, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
        -WorkingDirectory $appDir `
        -WindowStyle Minimized

    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $listening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    } until ($listening -or (Get-Date) -gt $deadline)
}

Start-Process $url
