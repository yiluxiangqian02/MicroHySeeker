$uchino_path = "MinerU\output\Dependence of the reverse current on the surface of electrode placed on_9ebe8347\content_list_v2.json"
$kim_path = "MinerU\output\cathodic-protection-system-against-a-reverse-current-after-shut-down-in-zero-gap-alkaline-water-electrolysis\content_list_v2.json"

function Print-Item($item) {
    Write-Host "---"
    $item | Get-Member -MemberType NoteProperty | ForEach-Object {
        $k = $_.Name
        $v = $item.$k
        if ($v -is [string]) {
            $val = if ($v.Length -gt 100) { $v.Substring(0, 100) + "..." } else { $v }
        } else {
            $val = $v | ConvertTo-Json -Compress
            if ($val.Length -gt 100) { $val = $val.Substring(0, 100) + "..." }
        }
        Write-Host "$k : $val"
    }
}

Write-Host "=== Uchino Structure (First 5) ==="
$uchino = Get-Content $uchino_path -Encoding UTF8 -Raw | ConvertFrom-Json
for ($i=0; $i -lt [Math]::Min(5, $uchino.Count); $i++) {
    Print-Item $uchino[$i]
}

Write-Host "`n=== Uchino Tables ==="
$uchino | Where-Object { $_.type -eq "table" } | ForEach-Object {
    Print-Item $_
}

Write-Host "`n=== Kim Images (First 5) ==="
if (Test-Path $kim_path) {
    $kim = Get-Content $kim_path -Encoding UTF8 -Raw | ConvertFrom-Json
    $kim_images = $kim | Where-Object { $_.type -eq "image" }
    for ($i=0; $i -lt [Math]::Min(5, $kim_images.Count); $i++) {
        Print-Item $kim_images[$i]
    }
}
