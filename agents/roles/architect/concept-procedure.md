# Concept definition playbook



The Capability Architect follows this sequence:

1. Identify business intent.
2. Identify owning bounded context.
3. Establish ubiquitous terminology.
4. Classify the block.
5. Define responsibility.
6. Define explicit non-responsibilities.
7. Define inputs.
8. Define outputs.
9. Define failures.
10. Define invariants.
11. Declare state ownership.
12. Declare observed state.
13. Declare side effects.
14. Declare required permissions.
15. Declare imports.
16. Declare exports.
17. Declare emitted and consumed events.
18. Evaluate design-pattern conditions.
19. Evaluate DDD rules.
20. Produce impact analysis.
21. Produce behavioral scenarios.
22. Evaluate applicable framework rules.
23. Stop before implementation.



For each step, record evidence in the pack. Ask the domain owner for missing mandatory semantics; until answered mark BLOCKED. Record intentional choices with Context, Decision, Alternatives, Consequences. Evaluate all rule IDs with evidence, including not-applicable explanations. Check direct dependency contracts without inspecting their implementations.

Pattern decisions: variation suggests Strategy; external translation requires Adapter; state-changing intent uses Command; lifecycle-dependent behavior suggests State; equivalent children suggest Composite. Evaluate remaining catalog conditions explicitly when present. Finish with exactly one status. No implementation plan is produced by this role.
