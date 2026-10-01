# Compatibility language

Versions use major.minor.patch. Major changes break public semantics, minor changes add backwards-compatible behavior, and patch changes clarify or correct without changing established expectations. Version labels alone do not prove compatibility.

Imports accept an exact version or ^MAJOR (for example ^1), meaning any published version of that major. Other range syntaxes are outside v0. Event references use @MAJOR and resolve through the contract registry. A new required input, narrower success guarantee, broader effect, or changed error semantics may be breaking even if shape is unchanged. Consumers must explicitly opt into a new major. Stability is experimental, stable, or deprecated and never permits silent breaking changes.
