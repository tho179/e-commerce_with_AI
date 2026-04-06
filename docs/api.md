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
- `GET /reviews/insights/?book_id=<id>`
- `GET /reviews/model-status/`
- `GET /recommendations/<customer_id>/`
- `GET /ai/drift/`
- `POST /ai/retrain/`
- `GET /search/semantic/?q=<query>&top_k=<n>`

## New Category Services

- `beauty-service`: `GET /products/`, `POST /products/`
- `grocery-service`: `GET /products/`, `POST /products/`
- `sports-service`: `GET /products/`, `POST /products/`

## Auth Service (JWT)

- `POST /auth/register/`
- `POST /auth/login/`
- `POST /auth/refresh/`
- `POST /auth/verify/`
- `POST /auth/users/role/` (internal admin sync)

Auth service operational notes:
- Container startup runs `python manage.py seed_admin` to ensure default admin exists.
- `POST /auth/users/role/` requires `X-Admin-Token` matching `AUTH_ADMIN_TOKEN`.

## Gateway Ops

- `GET /staff/ops/metrics/` (gateway metrics JSON)
- `GET /staff/ops/traces/` (gateway traces JSON)

## Internal Service Security

- Backend services now require `X-Service-Token` for non-health API calls.
- Public liveness endpoint `/health/` remains open for probes.
- Login/register endpoints have basic in-memory rate limiting.

## API Gateway (UI + Auth + Role Access)

- `GET /auth/login/`, `POST /auth/login/`
- `GET /auth/register/`, `POST /auth/register/`
- `POST /auth/logout/`
- `GET /shop/` (customer storefront, da nganh)
- `GET /shop/<product_id>/` (chi tiet san pham)
- `GET /customer/<customer_id>/favorites/` (danh sach yeu thich)
- `POST /customer/favorites/<product_id>/toggle/` (them/bo yeu thich)
- `GET /customer/cart/<customer_id>/` (checkout + orders + reviews)
- `GET /admin/users/`, `POST /admin/users/` (admin role assignment)
- `GET /staff/health/` (microservice health dashboard)

## Product Categories

- `sach`
- `quan_ao`
- `gia_dung`
- `dien_tu`
- `lam_dep`
- `tieu_dung`
- `the_thao`

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

### Trigger Retrain

`POST /ai/retrain/`

```json
{
  "source": "negative-spike",
  "note": "Detected strong negative review spike from event stream."
}
```

Both `source` and `note` are optional. If omitted, retrain uses defaults for manual trigger.

### AI-Enriched Review Response

```json
{
  "id": 12,
  "customer_id": 1,
  "book_id": 1000001,
  "rating": 4,
  "comment": "Giao hang cham nhung chat luong tot",
  "sentiment_label": "neutral",
  "sentiment_score": 0.58,
  "aspect_tags": ["delivery", "product_quality"],
  "advice": "Mo ticket voi doi logistics, kiem tra SLA va cap nhat ETA chu dong cho khach.",
  "ai_metadata": {
    "analyzer": {
      "model_kind": "deep-neural-net",
      "trained_on_reviews": 120,
      "minimum_required_reviews": 8
    },
    "aspect_hits": 2
  },
  "created_at": "2026-04-06T09:10:30.021Z"
}
```

### Review Insights Response

```json
{
  "book_id": 1000001,
  "scope": "book",
  "total_reviews": 42,
  "average_rating": 4.19,
  "average_sentiment_score": 0.754,
  "sentiment_distribution": {
    "positive": 30,
    "neutral": 9,
    "negative": 3
  },
  "top_aspects": [
    {"aspect": "delivery", "count": 14},
    {"aspect": "product_quality", "count": 10}
  ],
  "recommended_actions": [
    "Day manh cross-sell/upsell voi nhom san pham co sentiment cao."
  ],
  "status": {
    "model_kind": "deep-neural-net",
    "trained_on_reviews": 120,
    "minimum_required_reviews": 8
  }
}
```
