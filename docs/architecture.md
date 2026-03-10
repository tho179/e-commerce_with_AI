# Bookstore Microservice Architecture

## Overview

```mermaid
flowchart LR
    AG[api-gateway]
    CUS[customer-service]
    CART[cart-service]
    BOOK[book-service]
    CAT[catalog-service]
    ORD[order-service]
    PAY[pay-service]
    SHIP[ship-service]
    RATE[comment-rate-service]
    REC[recommender-ai-service]
    STAFF[staff-service]
    MAN[manager-service]

    AG --> BOOK
    AG --> CART
    AG --> CUS
    CUS --> CART
    CAT --> BOOK
    ORD --> CART
    ORD --> BOOK
    ORD --> PAY
    ORD --> SHIP
    REC --> BOOK
    REC --> RATE
```

## Service Boundaries

- `api-gateway`: server-rendered UI and request entry point for browsing books and carts.
- `customer-service`: customer registration and lookup. Customer creation also creates a cart.
- `cart-service`: cart ownership, add/update/delete cart items, view cart by customer.
- `book-service`: CRUD for books.
- `catalog-service`: local read model synchronized from `book-service`.
- `order-service`: order orchestration across cart, payment, and shipping.
- `pay-service`: payment reservation and cancellation.
- `ship-service`: shipment reservation and cancellation.
- `comment-rate-service`: customer ratings and reviews for books.
- `recommender-ai-service`: basic recommendation generation from reviews and catalog data.
- `staff-service`: staff directory.
- `manager-service`: manager directory.

## Current Transaction Flow

1. Customer is created in `customer-service`.
2. `customer-service` calls `cart-service` to create a cart.
3. Customer adds items in `cart-service`.
4. `order-service` reads cart data and book prices.
5. `order-service` reserves payment in `pay-service`.
6. `order-service` reserves shipping in `ship-service`.
7. If both reservations succeed, the order is confirmed.
8. If a reservation fails, successful downstream reservations are cancelled.

## Assignment 06 Gap

- Order orchestration is synchronous REST compensation, not a message-broker Saga yet.
- JWT auth-service, rate limiting, centralized logging, and metrics are not implemented yet.
- RabbitMQ or Kafka integration is still pending.