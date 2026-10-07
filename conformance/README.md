# Conformance

Store this project's acceptance mappings and verification evidence here as
admitted assignments produce them. This starter has no project conformance
claims. Schema validation alone does not establish behavioral conformance.

## Phase 3 readiness

The artifact-side prerequisites are specified and have reference checks:

| Area | 0.2.4 status | Evidence boundary |
| --- | --- | --- |
| Decision/rule history | Ready | Validator protects governed fields and supersession. |
| Structured types | Ready for local/context types | Nested validation and matching use one normalized tree; qualified imported namespaces are reserved. |
| Captures and typed events | Specified and validated | Paths/types and event payload artifacts are checked; no runner substitutes or executes them. |
| Value semantics | Specified with reference tests | Null, duration, number/decimal, NFC, enum and safe-integer behavior is unit-tested. |
| Time zone and collation | Artifact rules ready | `zoneinfo` validates names; tzdb/capability/DST evidence and locale execution await drivers. |
| Finding granularity/allowances | Ready | Exact visible findings are checked for MUT-01..40; default/verbose reporting and decision-backed allowances remain validator behavior. |
| Malformed-artifact robustness | Bounded evidence recorded | The deterministic 200-example fuzz profile and checked-in regression corpus have no crash or `INTERNAL_ERROR`; this is not a universal claim. |
| Scenario execution | Not delivered | No runner invokes an application or validates complete actual outputs. |
| Driver protocol/matrix | Not delivered | No driver implementation, result report or support matrix exists. |
| Cross-stack corpus | Metadata complete | Python, JavaScript, .NET and Kotlin/JVM probes are executed locally; Swift remains explicitly pending. The corpus is representation evidence, not conformance. |

The phase-3 prerequisite checklist is checked only for bounded artifact evidence:

- [x] Provenance protected: [decision log](../framework/decisions.yaml) and history-aware validation.
- [x] Captures unambiguous and typed: [validator regression suite](../tests/test_regressions.py).
- [x] Typed comparison at every depth: [matcher tests](../tests/test_match.py).
- [x] Value encoding, time zone and text rules defined: [value encoding protocol](protocol/value-encoding.md).
- [x] Validator robustness evidence: [pinned fuzz profile](../tests/test_robustness.py) and regressions.
- [x] One visible finding per declared cause: [MUT-01..40 assertions](../tests/test_mutations.py).
- [x] Serializer manifest lists every target stack: [serializer manifest](../tests/fixtures/serializers/manifest.yaml), including Swift pending status.

`scripts/aegis_match.py` is reference code for the matching specification. Its
tests demonstrate that the semantics are implementable; neither the module nor
the validator executes project scenarios or supplies behavioral conformance.
Phase 3 may build against these contracts, but executable conformance remains
open until runner, driver, complete-output, capability and real-stack behavioral
evidence exists.
