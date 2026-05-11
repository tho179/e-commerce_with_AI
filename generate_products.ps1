$headers = @{
    "X-Service-Token" = "bookstore-internal-token"   # <-- token đúng
}

# POWER SHELL: set output codepage to UTF-8 để tránh ký tự lỗi
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Post-Product {
    param(
        [string]$uri,
        [hashtable]$product
    )
    try {
        # Đặt header SPECIFICALLY khi gọi
        $body = $product | ConvertTo-Json -Depth 5
        $resp = Invoke-RestMethod -Method Post `
            -Uri $uri `
            -Headers $headers `
            -Body $body `
            -ContentType "application/json"
        Write-Host "✅ Đã thêm: $($product.sku)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Lỗi khi thêm $($product.sku): $($_.Exception.Message)" -ForegroundColor Red
    }
}

## 1️⃣ Sách – POST tới `/books/`
1..20 | ForEach-Object {
    Post-Product -uri "http://localhost:8002/books/" -product @{
        title       = "Book $_"  # Django model Book thường dùng 'title'
        description = "Sample book description $_"
        price       = [math]::Round(((Get-Random -Minimum 5 -Maximum 50) * 1.0), 2)
        category    = "book"
        sku         = "BK{0:D4}" -f $_
        stock       = Get-Random -Minimum 10 -Maximum 100
        author      = "Author $_"
    }
}

## 2️⃣ Fashion – POST tới `/fashion/`
1..20 | ForEach-Object {
    Post-Product -uri "http://localhost:8002/fashion/" -product @{
        name        = "Fashion Item $_" # Các model khác thường dùng 'name'
        description = "Trendy fashion product $_"
        price       = [math]::Round(((Get-Random -Minimum 20 -Maximum 200) * 1.0), 2)
        category    = "fashion"
        sku         = "FS{0:D4}" -f $_
        stock       = Get-Random -Minimum 5 -Maximum 80
    }
}

## 3️⃣ Laptop - POST tới `/laptop/`
1..15 | ForEach-Object {
    Post-Product -uri "http://localhost:8002/laptop/" -product @{
        name        = "Laptop Model $_"
        description = "High-performance laptop $_"
        price       = [math]::Round(((Get-Random -Minimum 500 -Maximum 2500) * 1.0), 2)
        category    = "laptop"
        sku         = "LT{0:D4}" -f $_
        stock       = Get-Random -Minimum 2 -Maximum 20
    }
}

## 4️⃣ Mobile - POST tới `/mobile/`
1..15 | ForEach-Object {
    Post-Product -uri "http://localhost:8002/mobile/" -product @{
        name        = "Mobile Phone $_"
        description = "Latest smartphone $_"
        price       = [math]::Round(((Get-Random -Minimum 200 -Maximum 1200) * 1.0), 2)
        category    = "mobile"
        sku         = "MB{0:D4}" -f $_
        stock       = Get-Random -Minimum 3 -Maximum 30
    }
}

Write-Host "Seeded 70+ products across categories." -ForegroundColor Cyan