$uchino_path = "MinerU\output\Dependence of the reverse current on the surface of electrode placed on_9ebe8347\content_list_v2.json"
$uchino = Get-Content $uchino_path -Encoding UTF8 -Raw | ConvertFrom-Json

$first_content_item = $uchino[0].content[0]
Write-Host "Keys in first content item: $($first_content_item | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name -join ', ')"

foreach ($item in $uchino) {
    for ($i=0; $i -lt $item.content.Count; $i++) {
        $c = $item.content[$i]
        $ctype = $item.type[$i]
        
        if ($ctype -eq "table") {
            Write-Host "Table at page $($item.page_idx). Keys: $($c | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name -join ', ')"
            if ($c.table_caption) { Write-Host "  Caption: $($c.table_caption)" }
            if ($c.table_body) { Write-Host "  Body preview: $($c.table_body.Substring(0, [Math]::Min(100, $c.table_body.Length)))" }
        }
        if ($ctype -eq "image") {
            Write-Host "Image at page $($item.page_idx). Keys: $($c | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name -join ', ')"
            if ($c.image_source) { Write-Host "  Path: $($c.image_source.path)" }
            if ($c.image_caption) { Write-Host "  Caption: $($c.image_caption)" }
        }
    }
}
