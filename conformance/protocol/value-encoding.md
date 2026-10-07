# Value encoding protocol

Status: normative for the phase 3 runner/driver boundary. Version: 0.2.4.

The runner sends typed inputs in the canonical JSON form below. A driver accepts
that form losslessly. Driver outputs may use any valid form listed here; the
runner validates and normalizes them before matching. JSON objects represent
records and maps, and JSON arrays represent lists. Enum values use their exact,
case-sensitive declared string.

| Aegis type | Canonical JSON form | Valid output constraints |
| --- | --- | --- |
| `string` | JSON string in NFC | Compared after NFC normalization; no trimming or case folding |
| `boolean` | JSON boolean | Strings and numbers are invalid |
| `integer` | JSON number | Integral and within `-9007199254740991..9007199254740991` |
| `number` | finite JSON number | Exact shortest round-trip decimal value; non-finite values are invalid |
| `decimal` | JSON string such as `"10.50"` | A finite base-10 string or JSON number; compare as an exact decimal |
| `date` | `YYYY-MM-DD` JSON string | A real Gregorian calendar date |
| `datetime` | RFC 3339 JSON string with an explicit offset | Same instant matches; runner expectation precision defines the half-open match window; only `T` or `t` separates date and time |
| `duration` | ISO 8601 JSON string | Normalize to `(years, months, fixed seconds)` |
| `id` | JSON string | Compared raw, without Unicode normalization |

An omitted optional record field and a field containing JSON `null` are the
same observable no-value. Drivers may emit either. A required field must be
present and non-null; omission and `null` are both contract errors. `$absent`
is scenario matcher syntax and never crosses the runner/driver boundary.

Runners MUST encode each typed input using the canonical form, reject unsafe
integers and non-finite numbers before dispatch, and accept every valid driver
output representation before applying typed matching. They MUST preserve the
decimal lexeme until it has been parsed as an exact decimal value.

Drivers MUST parse canonical decimals and integers without loss, preserve
explicit datetime offsets as instants, and treat scenario clock and timezone
as inputs. They MUST NOT use the host default timezone, locale, collation, or
Unicode normalization policy for business behavior. A driver without the
declared `timezone` capability reports a timezone scenario as `unsupported`.
Python drivers must use `datetime.isoformat()` or an equivalent RFC 3339
serializer. The space-separated form commonly produced by `str(datetime)` is
not a valid Aegis `datetime` and the runner rejects it.

Executable runner and driver conformance remains phase 3 work. The serializer
corpus in `tests/fixtures/serializers` verifies representation facts only; it
does not claim that a stack implements these business obligations.
