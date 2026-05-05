$ErrorActionPreference = "Stop"

$headers = @{ "X-Service-Token" = "bookstore-internal-token" }

function Invoke-JsonPost {
    param(
        [string]$Url,
        [hashtable]$Payload
    )

    return Invoke-RestMethod -Method Post -Uri $Url -Headers $headers -ContentType "application/json" -Body ($Payload | ConvertTo-Json -Depth 5)
}

$books = Invoke-RestMethod -Uri "http://localhost:8002/books/" -Headers $headers
if (-not $books -or $books.Count -lt 3) {
    throw "Not enough books found at product-service."
}

$bookIds = $books | Select-Object -First 6 -ExpandProperty id

$suffix = Get-Date -Format "yyyyMMddHHmmss"
$customers = @(
    @{ name = "Nguyen An"; email = ("an.nguyen.{0}@example.com" -f $suffix) },
    @{ name = "Tran Binh"; email = ("binh.tran.{0}@example.com" -f $suffix) },
    @{ name = "Le Chi"; email = ("chi.le.{0}@example.com" -f $suffix) }
)

$created = @()
foreach ($customer in $customers) {
    $createdCustomer = Invoke-JsonPost -Url "http://localhost:8012/customers/" -Payload $customer
    $created += $createdCustomer
}

foreach ($customer in $created) {
    $cart = $null
    for ($i = 0; $i -lt 5; $i++) {
        try {
            $cart = Invoke-RestMethod -Uri ("http://localhost:8003/carts/{0}/" -f $customer.id) -Headers $headers
            break
        } catch {
        }
    }

    if (-not $cart) {
        throw ("Cart not found for customer {0}." -f $customer.id)
    }

    $cartId = $cart.cart_id
    $items = @(
        @{ cart = $cartId; book_id = $bookIds[0]; quantity = 1 },
        @{ cart = $cartId; book_id = $bookIds[1]; quantity = 2 }
    )

    foreach ($item in $items) {
        Invoke-JsonPost -Url "http://localhost:8003/cart-items/" -Payload $item | Out-Null
    }

    Invoke-JsonPost -Url "http://localhost:8005/orders/" -Payload @{
        customer_id = $customer.id
        payment_method = "cod"
        shipping_method = "standard"
        shipping_address = "123 Sample Street, District 1, Ho Chi Minh City"
    } | Out-Null
}

"Seeded {0} customers, {1} carts, and {2} orders." -f $created.Count, $created.Count, $created.Count
