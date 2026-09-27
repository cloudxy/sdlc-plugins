Deliverable: {{OUTPUTS}}
Return: {{RETURN_RULE}}

For a v3 assignment, append exactly one fenced `result` JSON block with all fields: `methods_used` (objects with skill/reason/provenance="reported"), `reported_reads` (declared input IDs), `unresolved` (id/owner/blocks/item/severity), `proposed_changes` (target/change/evidence_refs), `product_delta` (text rows), `lessons` (verified text rows), `check_records` (paths to actual execution records). Use [] only when there are no items; a missing field is incomplete. Preserve the full report required above. Separate evidence from assertions; never self-declare execution_complete or stage acceptance. The manager saves the return and runs workflow.py record; producer roles do not update run records.
