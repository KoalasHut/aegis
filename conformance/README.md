# Conformance

Store this project's acceptance mappings and verification evidence here as
admitted assignments produce them. This starter has no project conformance
claims. Schema validation alone does not establish behavioral conformance.

## Phase 3 readiness

The artifact-side prerequisites are specified and have reference checks:

| Area | 0.2.3 status | Evidence boundary |
| --- | --- | --- |
| Decision/rule history | Ready | Validator protects governed fields and supersession. |
| Structured types | Ready for local/context types | Nested validation and matching use one normalized tree; qualified imported namespaces are reserved. |
| Captures and typed events | Specified and validated | Paths/types and event payload artifacts are checked; no runner substitutes or executes them. |
| Value semantics | Specified with reference tests | Null, duration, number/decimal, NFC, enum and safe-integer behavior is unit-tested. |
| Time zone and collation | Artifact rules ready | `zoneinfo` validates names; tzdb/capability/DST evidence and locale execution await drivers. |
| Finding granularity/allowances | Ready | Default/verbose reporting and decision-backed warning allowances are validator behavior. |
| Scenario execution | Not delivered | No runner invokes an application or validates complete actual outputs. |
| Driver protocol/matrix | Not delivered | No driver implementation, result report or support matrix exists. |
| Cross-stack corpus | Incomplete | Local feasibility exists for .NET, JavaScript and Python; Kotlin and Swift executable evidence is unavailable. |

`scripts/aegis_match.py` is reference code for the matching specification. Its
tests demonstrate that the semantics are implementable; neither the module nor
the validator executes project scenarios or supplies behavioral conformance.
Phase 3 may build against these contracts, but executable conformance remains
open until runner, driver, complete-output, capability and real-stack evidence exists.
