$actions = "view", "click", "search", "add_to_wishlist", "add_to_cart", "remove_from_cart", "checkout", "purchase"
$results = New-Object System.Collections.Generic.List[PSObject]
$startDate = Get-Date "2026-01-01T00:00:00Z"

for ($i = 1; $i -le 500; $i++) {
    $userId = "U" + $i.ToString("D4")
    foreach ($action in $actions) {
        $productId = "P" + (Get-Random -Minimum 1 -Maximum 1201).ToString("D4")
        $timestamp = $startDate.AddSeconds((Get-Random -Minimum 0 -Maximum 31536000)).ToString("yyyy-MM-ddTHH:mm:ssZ")
        $obj = [PSCustomObject]@{
            user_id    = $userId
            product_id = $productId
            action     = $action
            timestamp  = $timestamp
        }
        $results.Add($obj)
    }
}
$results | Export-Csv -Path "c:\bookstore-microservice\data_user500.csv" -NoTypeInformation -Encoding UTF8
$data = Import-Csv "c:\bookstore-microservice\data_user500.csv"
Write-Output "Total Rows: $($data.Count)"
Write-Output "Distinct Users: $(($data | Select-Object -ExpandProperty user_id -Unique).Count)"
Write-Output "Distinct Actions: $(($data | Select-Object -ExpandProperty action -Unique).Count)"
$data | Select-Object -First 5 | Format-Table
