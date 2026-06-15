$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 5174
while ($port -lt 5200) {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $port)
  try {
    $listener.Start()
    $listener.Stop()
    break
  } catch {
    $port += 1
  } finally {
    $listener.Stop()
  }
}

if ($port -ge 5200) {
  throw "No free simulator port found between 5174 and 5199."
}

Set-Location $scriptDir
Write-Host "Starting Pico setup simulator at http://127.0.0.1:$port"

if (Get-Command py -ErrorAction SilentlyContinue) {
  py -3 -m http.server $port --bind 127.0.0.1
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  python -m http.server $port --bind 127.0.0.1
} else {
  throw "Python was not found. Install Python or serve this folder with another static file server."
}
