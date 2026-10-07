#!/usr/bin/env bash
set -euo pipefail

cache_root="${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2/files-2.1"
find_jar() {
  local coordinate="$1"
  local version="$2"
  local filename="$3"
  find "$cache_root/$coordinate/$version" -name "$filename" -type f -print -quit
}

compiler="$(find_jar org.jetbrains.kotlin/kotlin-compiler-embeddable 2.1.20 kotlin-compiler-embeddable-2.1.20.jar)"
stdlib="$(find_jar org.jetbrains.kotlin/kotlin-stdlib 2.1.20 kotlin-stdlib-2.1.20.jar)"
reflect="$(find_jar org.jetbrains.kotlin/kotlin-reflect 2.1.20 kotlin-reflect-2.1.20.jar)"
trove="$(find_jar org.jetbrains.intellij.deps/trove4j 1.0.20200330 trove4j-1.0.20200330.jar)"
coroutines="$(find_jar org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm 1.8.0 kotlinx-coroutines-core-jvm-1.8.0.jar)"
databind="$(find_jar com.fasterxml.jackson.core/jackson-databind 2.11.1 jackson-databind-2.11.1.jar)"
core="$(find_jar com.fasterxml.jackson.core/jackson-core 2.11.1 jackson-core-2.11.1.jar)"
annotations="$(find_jar com.fasterxml.jackson.core/jackson-annotations 2.11.1 jackson-annotations-2.11.1.jar)"

for jar in "$compiler" "$stdlib" "$reflect" "$trove" "$coroutines" "$databind" "$core" "$annotations"; do
  test -n "$jar"
done

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
java -cp "$compiler:$stdlib:$reflect:$trove:$coroutines" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
  -no-stdlib -no-reflect -classpath "$stdlib:$databind:$core:$annotations" \
  -d "$out" "$here/Probe.kt"
java -cp "$out:$stdlib:$databind:$core:$annotations" ProbeKt
