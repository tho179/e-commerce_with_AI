# API Summary

## Core Services

- `GET /health/` on each service returns service status.
- `GET /books/`, `POST /books/`, `PUT /books/<book_id>/`, `DELETE /books/<book_id>/`
- `GET /customers/`, `POST /customers/`
- `GET /carts/`, `POST /carts/`, `GET /carts/<customer_id>/`
- `POST /cart-items/`, `PUT /cart-items/<item_id>/`, `DELETE /cart-items/<item_id>/`

## Added Services

- `GET /staff/`, `POST /staff/`
- `GET /managers/`, `POST /managers/`
- `GET /catalog/books/`, `POST /catalog/sync/`
- `GET /orders/`, `POST /orders/`
- `GET /payments/`, `POST /payments/reserve/`, `POST /payments/<payment_id>/cancel/`
- `GET /shipments/`, `POST /shipments/reserve/`, `POST /shipments/<shipment_id>/cancel/`
- `GET /reviews/`, `POST /reviews/`
- `GET /recommendations/<customer_id>/`

## Example Payloads

### Create Customer

```json
{
  "name": "Nguyen Xuan Dat",
  "email": "dat.nx@ptit.edu.vn"
}
```

### Add Cart Item

```json
{
  "cart": 1,
  "book_id": 1,
  "quantity": 2
}
```

### Create Order

```json
{
  "customer_id": 1,
  "payment_method": "cod",
  "shipping_method": "standard",
  "shipping_address": "Ha Noi"
}
```

### Create Review

```json
{
  "customer_id": 1,
  "book_id": 1,
  "rating": 5,
  "comment": "Rat hay"
}
```