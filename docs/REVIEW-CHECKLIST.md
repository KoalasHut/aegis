# Aegis pre-review checklist

Complete this checklist before requesting review. Link the command output or
fixture that supplies each checked item.

- [ ] Every new normative sentence has an `M-nn` example or validator fixture.
- [ ] Every new finding code has positive and negative fixtures and appears in exact-set assertions.
- [ ] Every new schema field is validated at every depth where it can appear.
- [ ] Value behavior is checked against every locally executable serializer corpus entry.
- [ ] The mutation suite includes an isolated case for every new validator check.
- [ ] Migration notes cover every change that can break an artifact under `--strict`.
- [ ] The changelog identifies every review finding fixed by the release.
- [ ] Matcher branch coverage is 100%, regressions pass, and repository validation passes with `--strict`.

Kotlin/JVM and Swift corpus entries may only be checked after their checked-in
probe runs on a pinned toolchain. Java output is supporting JVM evidence, not a
Kotlin serializer run. An unavailable stack remains explicitly deferred.
