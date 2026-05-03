# Library.HTTP(ailang)

## NAME
`Library.HTTP` — HTTP/1.1 client with URL parser, header handling, and TLS relay support

## SYNOPSIS
```
LibraryImport.HTTP
```
> Requires: `LibraryImport.Socket`, `LibraryImport.String`, `LibraryImport.HashMap`

## DESCRIPTION
HTTP provides a minimal but spec-compliant HTTP/1.1 client. It handles URL parsing, request construction, header management, and response parsing. TLS is deferred: the library recognises `https://` URLs and connects via a TLS relay proxy (external process) rather than implementing TLS natively.

The client is synchronous: a request blocks until the full response is received or a timeout fires.

| Feature | Detail |
|---|---|
| Protocol | HTTP/1.1 |
| Methods | GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH |
| TLS | Via relay proxy (https:// → plain TCP to relay) |
| Redirects | Up to 5 by default, configurable |
| Timeout | Configurable connect + read timeout |
| Chunked | Decoded transparently |
| Body size | Streamed to caller buffer, max configurable |

## FUNCTIONS

### Request Lifecycle

```
Function.HTTP.newClient
    Input:  —
    Output: Address  (client handle)
```
Allocates and returns a new HTTP client with default settings (5 redirects, 30s timeout, 4 MiB max body).

```
Function.HTTP.setTimeout
    Input:  client: Address, seconds: Integer
    Output: —
```

```
Function.HTTP.setMaxRedirects
    Input:  client: Address, max: Integer
    Output: —
```

```
Function.HTTP.setMaxBodySize
    Input:  client: Address, bytes: Integer
    Output: —
```

```
Function.HTTP.setHeader
    Input:  client: Address, name: Address, value: Address
    Output: —
```
Sets a default header applied to all subsequent requests on this client (e.g. `User-Agent`, `Authorization`).

```
Function.HTTP.clearHeaders
    Input:  client: Address
    Output: —
```
Clears all default headers.

### URL Parsing

```
Function.HTTP.parseURL
    Input:  url: Address
    Output: Address  (URL struct, or nil)
```
Parses a URL string into a structured representation.

```
Function.HTTP.urlScheme
    Input:  parsed: Address
    Output: Address  (String: "http" or "https")
```

```
Function.HTTP.urlHost
    Input:  parsed: Address
    Output: Address
```

```
Function.HTTP.urlPort
    Input:  parsed: Address
    Output: Integer  (0 if not specified)
```

```
Function.HTTP.urlPath
    Input:  parsed: Address
    Output: Address
```

```
Function.HTTP.urlQuery
    Input:  parsed: Address
    Output: Address  (raw query string or nil)
```

```
Function.HTTP.freeURL
    Input:  parsed: Address
    Output: —
```

### Execution

```
Function.HTTP.request
    Input:  client: Address, method: Address, url: Address, body: Address
    Output: Address  (Response struct, or nil)
```
Executes an HTTP request. `method` is a string (e.g. "GET"). `body` may be nil for GET/HEAD requests. The response is fully buffered before returning.

```
Function.HTTP.get
    Input:  client: Address, url: Address
    Output: Address
```
Convenience wrapper: `request` with method "GET" and nil body.

```
Function.HTTP.post
    Input:  client: Address, url: Address, body: Address
    Output: Address
```
Convenience wrapper: `request` with method "POST".

### Response Access

```
Function.HTTP.responseStatus
    Input:  resp: Address
    Output: Integer  (e.g. 200, 404)
```

```
Function.HTTP.responseHeaders
    Input:  resp: Address
    Output: Address  (HashMap of String→String)
```

```
Function.HTTP.responseBody
    Input:  resp: Address
    Output: Address  (raw body bytes)
```

```
Function.HTTP.responseBodyLen
    Input:  resp: Address
    Output: Integer
```

```
Function.HTTP.freeResponse
    Input:  resp: Address
    Output: —
```

### Cleanup

```
Function.HTTP.freeClient
    Input:  client: Address
    Output: —
```

## CONSTANTS

| Constant | Value | Meaning |
|---|---|---|
| `HTTP.GET` | 0 | |
| `HTTP.POST` | 1 | |
| `HTTP.PUT` | 2 | |
| `HTTP.DELETE` | 3 | |
| `HTTP.HEAD` | 4 | |
| `HTTP.OPTIONS` | 5 | |
| `HTTP.PATCH` | 6 | |
| `HTTP.REDIRECT_MAX` | 5 | Default max redirects |
| `HTTP.TIMEOUT_DEFAULT` | 30 | Default timeout in seconds |
| `HTTP.BODY_MAX_DEFAULT` | 4194304 | Default max body (4 MiB) |

## MEMORY

| Allocation | Freed by |
|---|---|
| Client handle | `freeClient` |
| URL struct | `freeURL` |
| Response struct | `freeResponse` |
| Response body buffer | Internal, freed with response |

## EXAMPLE

```ailang
LibraryImport.HTTP
LibraryImport.String

HTTP.newClient  → client
HTTP.setHeader  client  (String.literal "User-Agent")  (String.literal "AILang/1.0")

HTTP.get  client  (String.literal "http://example.com/api/status")  → resp

HTTP.responseStatus  resp  → status  # 200
HTTP.responseBody    resp  → body
String.print  body

HTTP.freeResponse  resp
HTTP.freeClient    client
```

## SEE ALSO
`Library.Socket` — underlying TCP transport
`Library.JSON` — typical payload format
`Library.String` — header/value manipulation

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
