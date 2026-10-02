# Conformance

Store this project's acceptance mappings and verification evidence here as
admitted assignments produce them. This starter has no project conformance
claims. Schema validation alone does not establish behavioral conformance.

## Phase 3 readiness

Phase 3 can start when all of these are true:

- Decision and rule history are protected.
- Captures are unambiguous.
- Value comparison is defined by contract type.
- Array matching is one-to-one.
- A tested reference matcher exists.

`scripts/aegis_match.py` is reference code for the matching specification. Its
tests demonstrate that the semantics are implementable; neither the module nor
the validator executes project scenarios or supplies conformance evidence.
