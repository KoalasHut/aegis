# Rule system

Rule files contain lists of records validated individually against rule.schema.json. IDs are stable and never reused. Scope identifies the governed artifacts. Verification type is structural, semantic, or review; automatable describes whether a structural check suffices, not whether a validator exists.

Failure severity is error for MUST/MUST NOT, warning for SHOULD/SHOULD NOT. A failed error rule means BLOCKED; warning deviations need justification. Assessment entries use pass, fail, not_applicable, or unknown with evidence. Unknown mandatory applicable rules block. VALID means no unresolved violations; VALID_WITH_WARNINGS means only justified warnings or nonblocking questions; BLOCKED means missing mandatory semantics or failures.

All initial rules are non-waivable as a conservative v0 policy. The waiver schema defines future artifacts only: reason, accountable owner, expiration date, and decision reference are mandatory. A future process must check eligibility, approval, expiration, and scope; a waiver file alone grants no exemption.

CMP is reserved; no numbered composition rules are defined in this baseline. composition.yaml intentionally contains an empty list; composition semantics are documented in the language specification.
