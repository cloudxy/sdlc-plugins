# ADR 0003: one repository per aggregate

Status: accepted (2026-08-12)

Persistence stays behind one repository per aggregate (OrderRepository for Order). Do not fold persistence into services: we swap the database adapter in tests (in-memory) and in production (Postgres).
