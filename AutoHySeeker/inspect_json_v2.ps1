$uchino_path = "MinerU\output\Dependence of the reverse current on the surface of electrode placed on_9ebe8347\content_list_v2.json"

$uchino = Get-Content $uchino_path -Encoding UTF8 -Raw | ConvertFrom-Json
Write-Host "Total items in root list: $($uchino.Count)"

Write-Host "`nStructure of the first item's content:"
$first_item = $uchino[0]
Write-Host "Item type array: $($first_item.type -join ', ')"
foreach ($c in $first_item.content) {
    Write-Host "  - Content type: $($c.type)"
    if ($c.type -eq "table") {
        Write-Host "    Table found! Keys: $($c | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name -join ', ')"
        if ($c.table_body) { Write-Host "    Table body (first 100 chars): $($c.table_body.Substring(0, [Math]::Min(100, $c.table_body.Length)))" }
    }
}

Write-Host "`nScanning all items for tables..."
foreach ($item in $uchino) {
    foreach ($c in $item.content) {
        if ($c.type -eq "table") {
            Write-Host "Table at page $($item.page_idx). Keys: $($c | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name -join ', ')"
            if ($c.table_caption) { Write-Host "  Caption: $($c.table_caption -join ' ')" }
            if ($c.table_body) { Write-Host "  Body preview: $($c.table_body.Substring(0, [Math]::Min(100, $c.table_body.Length)))" }
        }
    }
}

Write-Host "`nScanning all items for images..."
foreach ($item in $uchino) {
    foreach ($c in $item.content) {
        if ($c.type -eq "image") {
            Write-Host "Image at page $($item.page_idx). Path: $($c.image_source.path)"
            if ($c.image_caption) { Write-Host "  Caption: $($c.image_caption -join ' ')" }
        }
    }
}
