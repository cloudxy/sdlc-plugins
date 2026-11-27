# Accepted export contract
FR-1: export_cases(rows, tenant_id) returns CSV with id,title,status columns, in input order, containing only open cases belonging to tenant_id. Missing or blank tenant_id raises ValueError. An empty permitted set returns header only. Standard-library Python; preserve the function signature. Cross-tenant data must never appear. No database or deployment changes.
