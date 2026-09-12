#Requires -Version 5.1
<#
.SYNOPSIS
    Diagnoses why Modlunky 2 cannot reach spelunky.fyi.

.DESCRIPTION
    Some users see Modlunky 2 fail to connect to spelunky.fyi.

    This script checks things to identify potential issues:
      1. Which IP addresses spelunky.fyi resolves to.
      2. Whether each of those addresses completes a TLS handshake.
      3. What answers on port 443 when the handshake fails.
      4. Whether other HTTPS sites work, to tell one blocked site apart
         from a machine that cannot do HTTPS outside a browser.
      5. Whether a system proxy, PAC script or WPAD config is in play.
      6. Which antivirus and network filter drivers are installed.
      7. Which ISP the connection comes from, by ASN.

.PARAMETER Hostname
    Host to test. Defaults to spelunky.fyi.

.PARAMETER NoPause
    Skip the "Press Enter to close" prompt at the end.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\check-connection.ps1

.NOTES
    Results are also written to a text file so they can be attached to a bug
    report. The path is printed at the end.
#>

[CmdletBinding()]
param(
    [string] $Hostname = 'spelunky.fyi',
    [switch] $NoPause
)

$ErrorActionPreference = 'Continue'

$script:Lines = New-Object 'System.Collections.Generic.List[string]'

function Say {
    param([string] $Text = '', [string] $Color = 'Gray')
    $script:Lines.Add($Text)
    Write-Host $Text -ForegroundColor $Color
}

function Say-Header {
    param([string] $Text)
    Say ''
    Say "=== $Text ===" 'Cyan'
}

function New-ClientHello {
    param([string] $ServerName)
    function AddU16([System.Collections.Generic.List[byte]]$l, [int]$v) {
        $l.Add([byte](($v -shr 8) -band 0xFF)); $l.Add([byte]($v -band 0xFF))
    }
    $name = [Text.Encoding]::ASCII.GetBytes($ServerName)

    $sni = New-Object 'System.Collections.Generic.List[byte]'
    AddU16 $sni ($name.Length + 3); $sni.Add(0x00); AddU16 $sni $name.Length; $sni.AddRange($name)

    $ext = New-Object 'System.Collections.Generic.List[byte]'
    AddU16 $ext 0x0000; AddU16 $ext $sni.Count; $ext.AddRange($sni)
    AddU16 $ext 0x000a; AddU16 $ext 8; AddU16 $ext 6
    AddU16 $ext 0x001d; AddU16 $ext 0x0017; AddU16 $ext 0x0018
    AddU16 $ext 0x000b; AddU16 $ext 2; $ext.Add(0x01); $ext.Add(0x00)
    AddU16 $ext 0x000d; AddU16 $ext 8; AddU16 $ext 6
    AddU16 $ext 0x0403; AddU16 $ext 0x0804; AddU16 $ext 0x0401

    $body = New-Object 'System.Collections.Generic.List[byte]'
    AddU16 $body 0x0303
    $rnd = New-Object byte[] 32; (New-Object Random).NextBytes($rnd); $body.AddRange($rnd)
    $body.Add(0x00)
    AddU16 $body 10
    AddU16 $body 0xc02f; AddU16 $body 0xc02b; AddU16 $body 0xc030
    AddU16 $body 0xc02c; AddU16 $body 0x009c
    $body.Add(0x01); $body.Add(0x00)
    AddU16 $body $ext.Count; $body.AddRange($ext)

    $hs = New-Object 'System.Collections.Generic.List[byte]'
    $hs.Add(0x01)
    $hs.Add([byte](($body.Count -shr 16) -band 0xFF)); AddU16 $hs ($body.Count -band 0xFFFF)
    $hs.AddRange($body)

    $rec = New-Object 'System.Collections.Generic.List[byte]'
    $rec.Add(0x16); $rec.Add(0x03); $rec.Add(0x01); AddU16 $rec $hs.Count
    $rec.AddRange($hs)
    return $rec.ToArray()
}

function Format-HexDump {
    param([byte[]] $Bytes, [int] $Count, [int] $MaxLines = 8)
    $out = @()
    $shown = [Math]::Min($Count, $MaxLines * 16)
    for ($i = 0; $i -lt $shown; $i += 16) {
        $len = [Math]::Min(16, $shown - $i)
        $chunk = $Bytes[$i..($i + $len - 1)]
        $hex = ($chunk | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
        $asc = -join ($chunk | ForEach-Object { if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } else { '.' } })
        $out += ('  {0:X4}  {1,-47}  {2}' -f $i, $hex, $asc)
    }
    if ($Count -gt $shown) { $out += ("  ... {0} more bytes" -f ($Count - $shown)) }
    return $out
}

function Test-TlsHost {
    param([string] $Name)
    $tcp = $null; $ssl = $null; $connected = $false
    try {
        $tcp = New-Object Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($Name, 443, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(5000)) { throw 'timed out' }
        $tcp.EndConnect($iar); $connected = $true
        $ssl = New-Object Net.Security.SslStream($tcp.GetStream(), $false,
            [Net.Security.RemoteCertificateValidationCallback] { $true })
        $ssl.AuthenticateAsClient($Name)
        return 'OK'
    }
    catch {
        if ($connected) { return 'FAILED' } else { return 'UNREACHABLE' }
    }
    finally {
        if ($ssl) { $ssl.Dispose() }
        if ($tcp) { $tcp.Close() }
    }
}

$script:Problems = New-Object 'System.Collections.Generic.List[string]'
function Flag { param([string] $Text) $script:Problems.Add($Text) }


Say "Modlunky 2 connection check" 'White'
Say "Host      : $Hostname"
Say "Run at    : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Say "Windows   : $([Environment]::OSVersion.VersionString)"
Say "PowerShell: $($PSVersionTable.PSVersion)"

Say-Header 'Network'
try {
    $info = Invoke-RestMethod -Uri 'https://ipinfo.io/json' -TimeoutSec 5 -ErrorAction Stop
    if ($info.org) { Say ("  ISP    : {0}" -f $info.org) } else { Say "  ISP    : unknown" }
    if ($info.region -or $info.country) { Say ("  Region : {0}, {1}" -f $info.region, $info.country) }
}
catch {
    Say "  could not look up ISP: $($_.Exception.GetBaseException().Message)" 'Yellow'
}

Say-Header 'DNS'
$addresses = @()
try {
    $addresses = [Net.Dns]::GetHostAddresses($Hostname) | ForEach-Object { $_.IPAddressToString }
    foreach ($ip in $addresses) { Say "  $ip" }
}
catch {
    Say "  DNS lookup failed: $($_.Exception.GetBaseException().Message)" 'Red'
    Flag 'DNS lookup failed. The machine cannot resolve the site at all.'
}

$privatePattern = '^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2[0-9]|3[01])\.|::1$|fe80:|f[cd])'
foreach ($ip in $addresses) {
    if ($ip -match $privatePattern) {
        Say "  ^ $ip is a private or loopback address" 'Red'
        Flag "DNS returned $ip, a private address. Something is redirecting the site locally."
    }
}

Say-Header 'TLS certificate'

$v6ok = 0; $v6fail = 0; $v6noroute = 0
$v4ok = 0; $v4fail = 0; $v4noroute = 0
$badIssuer = $null
$failedAddress = $null
$failedAddressIsV6 = $false

if (-not $addresses) {
    Say "  skipped, nothing resolved" 'Yellow'
}

foreach ($ip in $addresses) {
    $addr = [Net.IPAddress]::Parse($ip)
    $fam = if ($addr.AddressFamily -eq 'InterNetworkV6') { 'IPv6' } else { 'IPv4' }
    $tcp = $null
    $ssl = $null
    $connected = $false
    Say ("  {0}  {1}" -f $fam, $ip)
    try {
        $tcp = New-Object Net.Sockets.TcpClient($addr.AddressFamily)

        $iar = $tcp.BeginConnect($addr, 443, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(5000)) { throw 'timed out after 5s' }
        $tcp.EndConnect($iar)
        $connected = $true

        $acceptAny = [Net.Security.RemoteCertificateValidationCallback] { $true }
        $ssl = New-Object Net.Security.SslStream($tcp.GetStream(), $false, $acceptAny)
        $ssl.AuthenticateAsClient($Hostname)

        $issuer = $ssl.RemoteCertificate.Issuer
        Say ("        OK           {0}, issuer {1}" -f $ssl.SslProtocol, $issuer) 'Green'
        if ($fam -eq 'IPv6') { $v6ok++ } else { $v4ok++ }
        if ($issuer -notmatch 'Google Trust Services') { $badIssuer = $issuer }
    }
    catch {
        $msg = $_.Exception.GetBaseException().Message
        if (-not $connected) {
            Say ("        UNREACHABLE  {0}" -f $msg) 'Yellow'
            if ($fam -eq 'IPv6') { $v6noroute++ } else { $v4noroute++ }
        }
        else {
            Say ("        FAILED       {0}" -f $msg) 'Red'
            if (-not $failedAddress -or ($fam -eq 'IPv4' -and $failedAddressIsV6)) {
                $failedAddress = $ip
                $failedAddressIsV6 = ($fam -eq 'IPv6')
            }
            if ($fam -eq 'IPv6') { $v6fail++ } else { $v4fail++ }
        }
    }
    finally {
        if ($ssl) { $ssl.Dispose() }
        if ($tcp) { $tcp.Close() }
    }
}


if ($v6noroute -gt 0 -and $v6ok -eq 0 -and $v6fail -eq 0) {
    Say "  note: no IPv6 connectivity on this machine"
}

if ($badIssuer) {
    Flag "The certificate was issued by '$badIssuer' instead of Google Trust Services. Something is intercepting HTTPS."
}

if ($v6fail -gt 0 -and $v6ok -eq 0 -and $v4ok -gt 0) {
    Flag ("IPv6 connects but HTTPS over it fails, while IPv4 works. The IPv6 path to $Hostname is broken. " +
        "Browsers try both and fall back. Modlunky 2 uses whichever address Windows returns first.")
}
elseif ($v4fail -gt 0 -and $v4ok -eq 0 -and $v6ok -gt 0) {
    Flag "IPv4 fails but IPv6 works to $Hostname."
}
elseif (($v4ok + $v6ok) -eq 0 -and ($v4fail + $v6fail) -gt 0) {
    Flag "No address completed a TLS handshake. Windows' own TLS stack cannot connect either."
}
elseif (($v4ok + $v6ok) -eq 0) {
    Flag "Could not reach $Hostname on any address."
}

if (($v4fail + $v6fail) -gt 0) {
    Say-Header 'What is answering on port 443'
    $target = $failedAddress
    try {
        $hello = New-ClientHello -ServerName $Hostname

        $paddr = [Net.IPAddress]::Parse($target)
        $tcp = New-Object Net.Sockets.TcpClient($paddr.AddressFamily)
        $iar = $tcp.BeginConnect($paddr, 443, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(5000)) { throw 'timed out' }
        $tcp.EndConnect($iar)
        $st = $tcp.GetStream(); $st.ReadTimeout = 5000
        $st.Write($hello, 0, $hello.Length)
        $buf = New-Object byte[] 2048
        $n = 0
        try {
            while ($n -lt $buf.Length) {
                $r = $st.Read($buf, $n, $buf.Length - $n)
                if ($r -le 0) { break }
                $n += $r
            }
        }
        catch { }
        $tcp.Close()

        if ($n -le 0) {
            Say "  $target closed the connection without replying"
        }
        else {
            Say ("  {0} replied with {1} bytes, first byte 0x{2:X2}" -f $target, $n, $buf[0])
            if ($buf[0] -ge 0x14 -and $buf[0] -le 0x18) {
                Say "  that is valid TLS, so the failure is in the handshake itself"
            }
            else {
                Say "  that is not TLS" 'Red'

                $printable = @($buf[0..($n - 1)] | Where-Object { $_ -ge 32 -and $_ -lt 127 }).Count
                $distinct = @($buf[0..($n - 1)] | Sort-Object -Unique).Count

                if ($distinct -eq 1) {
                    Say ("  all {0} bytes are 0x{1:X2}." -f $n, $buf[0]) 'Yellow'
                }
                elseif ($printable -gt ($n / 2)) {
                    Say "  readable content follows:" 'Yellow'
                    $text = -join ($buf[0..($n - 1)] | ForEach-Object {
                            if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } elseif ($_ -eq 10) { "`n" } else { '.' } })
                    foreach ($line in ($text -split "`n")) { if ($line.Trim()) { Say "    $($line.Trim())" 'Yellow' } }
                }
                else {
                    Say ("  reply is binary, {0} of {1} bytes printable" -f $printable, $n) 'Yellow'
                }

                foreach ($line in (Format-HexDump -Bytes $buf -Count $n)) { Say $line }
                Flag "Something answered port 443 without speaking TLS."
            }
        }
    }
    catch {
        Say "  could not probe: $($_.Exception.GetBaseException().Message)" 'Yellow'
    }
}

if (($v4ok + $v6ok) -eq 0 -and $addresses) {
    Say-Header 'Other sites'
    $controls = @{}
    foreach ($h in 'cloudflare.com', 'github.com', 'www.microsoft.com') {
        $r = Test-TlsHost -Name $h
        $controls[$h] = $r
        $color = if ($r -eq 'OK') { 'Green' } else { 'Red' }
        Say ("  {0,-20} {1}" -f $h, $r) $color
    }
    $okCount = ($controls.Values | Where-Object { $_ -eq 'OK' }).Count
    if ($okCount -eq $controls.Count) {
        Flag "Other HTTPS sites work, only $Hostname fails."
    }
    elseif ($okCount -eq 0) {
        Flag "Every HTTPS site tested fails outside a browser. Something on this machine is intercepting non-browser HTTPS, most likely antivirus or security software."
    }
    else {
        Flag "Some HTTPS sites work and others do not, so filtering is selective."
    }
}

Say-Header 'Proxy'
try {
    $winhttp = (netsh winhttp show proxy 2>&1 | Out-String).Trim()
    foreach ($line in ($winhttp -split "`r?`n")) {
        if ($line.Trim()) { Say "  $($line.Trim())" }
    }
}
catch {
    Say "  could not read WinHTTP proxy settings" 'Yellow'
}

try {
    $ie = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop
    Say ("  ProxyEnable   : {0}" -f $ie.ProxyEnable)
    Say ("  ProxyServer   : {0}" -f $ie.ProxyServer)
    Say ("  AutoConfigURL : {0}" -f $ie.AutoConfigURL)

    if ($ie.ProxyEnable -eq 1) {
        Flag "A manual proxy is configured ($($ie.ProxyServer)). Traffic goes through another server."
    }
    if ($ie.AutoConfigURL) {
        Flag ("This machine gets its proxy from a PAC script at $($ie.AutoConfigURL). " +
            "Modlunky 2 cannot read PAC scripts.")
    }
}
catch {
    Say "  could not read Internet Settings" 'Yellow'
}

$wpadEnabled = $false
try {
    $conn = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections'
    $blob = (Get-ItemProperty $conn -Name DefaultConnectionSettings -ErrorAction Stop).DefaultConnectionSettings
    if ($blob -and $blob.Length -gt 8) {
        $f = $blob[8]
        $wpadEnabled = [bool]($f -band 0x08)
        Say ("  Autoconfig flags : 0x{0:X2}  (manual={1}, PAC={2}, WPAD={3})" -f `
                $f, [bool]($f -band 0x02), [bool]($f -band 0x04), $wpadEnabled)
    }
}
catch {
    Say "  no saved connection settings to read"
}

if ($wpadEnabled) {
    try {
        $wpad = Invoke-WebRequest -Uri 'http://wpad/wpad.dat' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop

        $wpadBody = $wpad.Content
        if ($wpadBody -is [byte[]]) { $wpadBody = [Text.Encoding]::UTF8.GetString($wpadBody) }

        if ($wpadBody -match 'FindProxyForURL') {
            Say "  WPAD           : this network is serving a proxy config at http://wpad/wpad.dat" 'Red'
            Flag ("The network hands out a proxy automatically via WPAD.")
        }
        else {
            Say "  WPAD           : nothing served on this network (normal)"
        }
    }
    catch {
        Say "  WPAD           : nothing served on this network (normal)"
    }
}

Say-Header 'Security software'
$thirdPartyAv = @()
try {
    $av = @(Get-CimInstance -Namespace 'root\SecurityCenter2' -ClassName AntiVirusProduct -ErrorAction Stop)
    if ($av.Count -eq 0) { Say "  antivirus     : none registered" }
    foreach ($a in $av) {
        Say ("  antivirus     : {0}" -f $a.displayName)
        if ($a.displayName -notmatch 'Windows Defender|Microsoft Defender') { $thirdPartyAv += $a.displayName }
    }
}
catch {
    Say "  could not read registered antivirus" 'Yellow'
}

try {
    foreach ($f in @(Get-CimInstance -Namespace 'root\SecurityCenter2' -ClassName FirewallProduct -ErrorAction Stop)) {
        Say ("  firewall      : {0}" -f $f.displayName)
    }
}
catch { }

$filters = @()
try {
    $filters = @(Get-NetAdapterBinding -ErrorAction Stop |
        Where-Object { $_.Enabled -and $_.ComponentID -notlike 'ms_*' })
    if ($filters.Count -eq 0) { Say "  filter driver : none" }
    foreach ($f in $filters) { Say ("  filter driver : {0} ({1})" -f $f.DisplayName, $f.ComponentID) 'Yellow' }
}
catch {
    Say "  could not read network adapter bindings"
}

if (($v4ok + $v6ok) -eq 0) {
    if ($thirdPartyAv.Count -gt 0) {
        Flag "Third-party antivirus installed: $($thirdPartyAv -join ', '). HTTPS scanning in these products intercepts connections."
    }
    if ($filters.Count -gt 0) {
        Flag "A third-party driver is bound into the network stack and can intercept HTTPS."
    }
}

Say-Header 'Summary'
if ($script:Problems.Count -eq 0) {
    Say "  Nothing unusual found. The connection to $Hostname looks clean from here." 'Green'
}
else {
    foreach ($p in $script:Problems) { Say "  - $p" 'Yellow' }
}

$outFile = Join-Path $env:TEMP 'modlunky2-connection-check.txt'
try {
    $script:Lines | Out-File -FilePath $outFile -Encoding utf8
    Say ''
    Say "Saved a copy to: $outFile" 'Cyan'
}
catch {
    Say ''
    Say "Could not save a copy: $($_.Exception.Message)" 'Yellow'
}

if (-not $NoPause) {
    Write-Host ''
    Read-Host 'Press Enter to close' | Out-Null
}
