# Review Intelligence Knowledge Base

## Goal

Create a reusable knowledge base so review signals can be mapped to operational and business actions.

## Taxonomy

- delivery: shipping speed, late delivery, fulfillment handoff.
- product_quality: defect, durability, mismatch, quality perception.
- pricing_value: expensive/cheap/fair-value, promotion fit.
- customer_service: support quality, response speed, empathy.
- packaging: box condition, seal integrity, damage in transit.

## Action Playbook

### delivery

- Positive: push fast-shipping badge and advertise SLA.
- Neutral: monitor SLA by region/carrier.
- Negative: open logistics incident and proactive ETA update.

### product_quality

- Positive: amplify UGC and trust content for this SKU.
- Neutral: observe defect trend by batch.
- Negative: start QA investigation and temporary suppression if needed.

### pricing_value

- Positive: run bundle or premium upsell.
- Neutral: A/B test discount depth.
- Negative: benchmark competitors and adjust couponing strategy.

### customer_service

- Positive: reuse successful response templates.
- Neutral: monitor FRT and CSAT by team.
- Negative: trigger support quality review and retraining.

### packaging

- Positive: keep current packaging SOP.
- Neutral: track damage rate by carrier.
- Negative: upgrade packaging material and run warehouse audit.

## Data Contract

Structured file used by service:

- comment-rate-service/app/knowledge_base/review_playbook.json

Service output fields tied to KB:

- aspect_tags
- advice
- ai_metadata.aspect_hits

## Governance

- Update KB monthly with operations + CS + product teams.
- Version KB and track changes in git.
- Validate effect via KPI: conversion_rate, return_rate, CSAT, cancellation_rate.
