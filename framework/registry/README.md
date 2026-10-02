# Registry semantics

Registry paths resolve relative to `framework/`. IDs and versions uniquely identify entries. Contexts own terminology; blocks identify Concept Packs; contracts index public exports or explicit dependency specifications. A dependency specification is an assumed contract, not an implemented or approved provider. No provider discovery or runtime resolution exists.

`contexts.yaml`, `blocks.yaml`, `contracts.yaml`, and `rules.yaml` each contain a YAML list. They start as `[]`, meaning no registered artifacts. Templates and illustrative examples must not be registered as approved project contracts. Add entries only for project artifacts under an authorized assignment, with status and approval provenance supported by review.

Context entries identify `id`, `summary`, and a project-relative `path`; block entries identify `id`, `version`, `boundedContext`, `path`, and reviewed `status`; contract entries identify `id`, `version`, `boundedContext`, `path`, and `role` (`export` or `dependency-specification`). A registry entry does not itself grant approval.

Rule entries identify `id`, `context`, `status`, and the project-relative themed-file `path`. Retain deprecated IDs in the registry so that an ID is never reused. A rule's decision reference is recorded in its canonical rule record; registry inclusion does not approve it.
