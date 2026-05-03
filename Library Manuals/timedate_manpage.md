# Library.TimeDate(ailang)

## NAME
`Library.TimeDate` — monotonic and wall-clock time, ISO 8601 formatting, and date arithmetic

## SYNOPSIS
```
LibraryImport.TimeDate
```
> Requires: none (thin over POSIX clock_gettime / gettimeofday via AILang FFI)

## DESCRIPTION
TimeDate provides two clocks: a high-resolution **monotonic** clock (unaffected by system time adjustments) for measuring intervals, and the system **wall clock** (UTC) for timestamps and human-readable dates. It also includes ISO 8601 formatting, parsing, and basic date arithmetic (add days, compare dates).

| Concept | Detail |
|---|---|
| Monotonic source | CLOCK_MONOTONIC (or mach_absolute_time on macOS) |
| Wall source | CLOCK_REALTIME (UTC) |
| Resolution | Microseconds (monotonic), seconds (wall for date ops) |
| Epoch | Unix epoch (1970-01-01T00:00:00Z) |
| Format | ISO 8601 subset: `YYYY-MM-DDTHH:MM:SS[.sss]Z` |

## FUNCTIONS

### Monotonic Clock

```
Function.TimeDate.tick
    Input:  —
    Output: Integer  (microseconds from an arbitrary origin)
```
Returns the current value of the monotonic clock in microseconds. The origin is arbitrary (typically system boot). Suitable for measuring elapsed time between two calls. Wraps around on 64-bit overflow (≈292,000 years).

```
Function.TimeDate.elapsed
    Input:  start: Integer
    Output: Integer  (microseconds since start)
```
Convenience: `tick() - start`. Always non-negative assuming the clock has not wrapped.

```
Function.TimeDate.sleep
    Input:  microseconds: Integer
    Output: —
```
Blocks the calling context for at least `microseconds` microseconds. May sleep longer due to scheduler granularity.

### Wall Clock

```
Function.TimeDate.now
    Input:  —
    Output: Integer  (Unix timestamp, seconds since epoch)
```
Returns the current UTC wall-clock time as an integer Unix timestamp.

```
Function.TimeDate.nowMillis
    Input:  —
    Output: Integer  (milliseconds since epoch)
```

```
Function.TimeDate.nowMicros
    Input:  —
    Output: Integer  (microseconds since epoch)
```

### Formatting

```
Function.TimeDate.format
    Input:  timestamp: Integer, format: Address
    Output: Address  (String)
```
Formats a Unix timestamp according to a strftime-like `format` string. Specifiers:

| Specifier | Output |
|---|---|
| `%Y` | 4-digit year |
| `%m` | 2-digit month (01–12) |
| `%d` | 2-digit day (01–31) |
| `%H` | 2-digit hour (00–23) |
| `%M` | 2-digit minute (00–59) |
| `%S` | 2-digit second (00–59) |
| `%%` | Literal `%` |

```
Function.TimeDate.formatISO
    Input:  timestamp: Integer
    Output: Address  (String in ISO 8601)
```
Formats as `YYYY-MM-DDTHH:MM:SSZ` (UTC, no fractional seconds).

```
Function.TimeDate.formatISOMs
    Input:  timestampMs: Integer
    Output: Address
```
Formats with millisecond precision: `YYYY-MM-DDTHH:MM:SS.sssZ`.

### Parsing

```
Function.TimeDate.parseISO
    Input:  str: Address
    Output: Integer  (Unix timestamp, or -1 on error)
```
Parses an ISO 8601 string (with or without `Z`, with or without fractional seconds) into a Unix timestamp. Returns -1 on parse failure.

```
Function.TimeDate.parseFormat
    Input:  str: Address, format: Address
    Output: Integer  (timestamp, or -1)
```
Parses a date string according to the given strftime-like format.

### Date Components

```
Function.TimeDate.year
    Input:  timestamp: Integer
    Output: Integer  (e.g. 2026)
```

```
Function.TimeDate.month
    Input:  timestamp: Integer
    Output: Integer  (1–12)
```

```
Function.TimeDate.day
    Input:  timestamp: Integer
    Output: Integer  (1–31)
```

```
Function.TimeDate.hour
    Input:  timestamp: Integer
    Output: Integer  (0–23)
```

```
Function.TimeDate.minute
    Input:  timestamp: Integer
    Output: Integer  (0–59)
```

```
Function.TimeDate.second
    Input:  timestamp: Integer
    Output: Integer  (0–59)
```

```
Function.TimeDate.weekday
    Input:  timestamp: Integer
    Output: Integer  (0=Sunday, 1=Monday … 6=Saturday)
```

### Date Arithmetic

```
Function.TimeDate.addDays
    Input:  timestamp: Integer, days: Integer
    Output: Integer  (new timestamp)
```
Adds or subtracts (negative `days`) calendar days, accounting for DST transitions.

```
Function.TimeDate.addSeconds
    Input:  timestamp: Integer, seconds: Integer
    Output: Integer
```

```
Function.TimeDate.diffDays
    Input:  a: Integer, b: Integer
    Output: Integer  (signed day difference, a - b)
```
Calendar day difference (ignores time-of-day).

```
Function.TimeDate.diffSeconds
    Input:  a: Integer, b: Integer
    Output: Integer
```
Exact second difference.

```
Function.TimeDate.isLeapYear
    Input:  year: Integer
    Output: Integer  (1 = leap, 0 = common)
```

## MEMORY

| Allocation | Freed by |
|---|---|
| Formatted strings | Caller |
| Internal buffers | None (stack-allocated) |

## EXAMPLE

```ailang
LibraryImport.TimeDate
LibraryImport.String

# Measure elapsed time
TimeDate.tick  → start
# ... work ...
TimeDate.elapsed  start  → us
String.print  (String.concat  (String.literal "Elapsed: ")  (String.fromInt us))  

# Timestamp
TimeDate.now  → ts
TimeDate.formatISO  ts  → s  # "2026-05-15T18:30:00Z"
String.print  s

# Date arithmetic
TimeDate.addDays  ts  30  → future
TimeDate.diffDays  future  ts  → n  # 30
TimeDate.weekday    future  → wd  # 0–6
```

## SEE ALSO
`Library.String` — string formatting helpers

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
