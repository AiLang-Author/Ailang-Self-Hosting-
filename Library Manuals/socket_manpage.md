# Library.Socket (ailang)

## NAME
`Library.Socket` — TCP and Unix domain sockets via raw Linux syscalls

## SYNOPSIS
```ailang
LibraryImport.Socket
```
> Requires: none (direct syscall interface, no other AILang libraries)

## DESCRIPTION

Socket is a thin, zero-dependency wrapper over the Linux socket syscall API.
It operates on **integer file descriptors** — there are no opaque handle
types. The caller manages fd lifecycle and buffer allocation.

Two address families are supported:

| Family | Constant | Use |
|--------|----------|-----|
| IPv4 | `AF_INET` (2) | TCP to remote hosts |
| IPv6 | `AF_INET6` (10) | TCP via IPv6 |
| Unix | `AF_UNIX` (1) | Local IPC (abstract namespace supported) |

All functions return raw syscall results. Errors are reported as negative
return values; the library prints diagnostic messages to stdout on failure.

---

## CONSTANTS

### SocketConstants

| Constant | Value | Meaning |
|----------|-------|---------|
| `AF_INET`     | 2  | IPv4 address family |
| `AF_INET6`    | 10 | IPv6 address family |
| `SOCK_STREAM` | 1  | TCP stream socket |
| `SOCK_DGRAM`  | 2  | UDP datagram socket |
| `IPPROTO_TCP` | 6  | TCP protocol |
| `SOL_SOCKET`  | 1  | Socket-level option |
| `SO_REUSEADDR`| 2  | Reuse local address |
| `SO_KEEPALIVE`| 9  | Keep connections alive |
| `MSG_NOSIGNAL`| 16384 | Suppress SIGPIPE |

### Syscall numbers (raw)

| Call | Number | Used by |
|------|--------|---------|
| `read`    | 0  | `Recv`, `RecvExact`, `RecvMsg` |
| `write`   | 1  | `Send`, `SendMsg` |
| `close`   | 3  | `Close` |
| `socket`  | 41 | `Create` |
| `connect` | 42 | `Connect`, `ConnectUnix` |
| `accept`  | 43 | `Accept` |
| `bind`    | 49 | `BindUnix` |
| `listen`  | 50 | `Listen` |
| `setsockopt` | 54 | `SetRecvTimeout` |
| `fcntl`   | 72 | `SetNonBlock` |
| `unlink`  | 87 | `BindUnix` (removes stale socket file) |

---

## IPv4 TCP CLIENT

### Create a socket

```
Socket.Create(family, type)  → Integer (fd)
```

Calls `socket(family, type, 0)`. Returns the fd on success, **-1** on failure.
For TCP: `Socket.Create(SocketConstants.AF_INET, SocketConstants.SOCK_STREAM)`.

### Build an address

```
Socket.CreateAddr(host, port)  → Address (16-byte sockaddr_in)
```

Allocates and returns a **16-byte `sockaddr_in`** structure. The caller must
`Deallocate` it after use (size 16).

`host` is a string. If it equals `"localhost"` or `"127.0.0.1"`, the loopback
address `127.0.0.1` is used. Otherwise, `ParseIPAddress` is called to parse
a dotted-quad `"x.x.x.x"` string.

`port` is an integer in host byte order (converted to network byte order
internally).

Layout:
| Offset | Size | Field |
|--------|------|-------|
| 0  | 2 | `sin_family` = AF_INET (2) |
| 2  | 2 | `sin_port` (network byte order) |
| 4  | 4 | `sin_addr.s_addr` (network byte order) |
| 8  | 8 | Zero padding |

### Connect

```
Socket.Connect(sock, addr)  → Integer (0 = success, -1 = error)
```

Calls `connect(sock, addr, 16)`. The `addr` must be a 16-byte `sockaddr_in`
from `CreateAddr`.

### Send / Recv

```
Socket.Send(sock, buffer, length)    → Integer (bytes sent, or -1)
Socket.Recv(sock, buffer, max_len)   → Integer (bytes received, 0 = closed, -1 = error)
Socket.RecvExact(sock, buffer, len)  → Integer (total bytes read, 0 = failure)
```

`Send` and `Recv` are direct wrappers over `write(2)` and `read(2)`.

`RecvExact` loops until exactly `len` bytes are read or a short/error read
occurs. Returns the total bytes read (should equal `len` on success, 0 on
failure or premature close).

### Set receive timeout

```
Socket.SetRecvTimeout(sock, timeout_ms)  → void (always returns 0)
```

Calls `setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, ...)`. Allocates a temporary
`struct timeval` internally.

### Parse an IP string

```
Socket.ParseIPAddress(ip_str)  → Address (32-byte array of 4 Integers)
```

Parses `"x.x.x.x"` into a 4-element array. Each element is an 8-byte integer
(use `ArrayGet` to retrieve). The caller must `ArrayDestroy` the result.

### Close

```
Socket.Close(sock)  → void
```

Calls `close(sock)`. Safe to call on invalid fds; the kernel will return an
error silently ignored.

---

## UNIX DOMAIN SOCKETS (Local IPC)

These functions extend the IPv4 API for local inter-process communication.
Abstract namespace sockets (prefixed with `@`) are supported — they live in
the kernel namespace and avoid WSL2 tmpfs inode bugs.

### Build a Unix address

```
Socket.CreateAddrUnix(path)  → Address (110-byte sockaddr_un)
```

Allocates a 110-byte `sockaddr_un` structure. `path` is a filesystem path or
an abstract name. If the first character is `@` (0x40), it is replaced with a
null byte (Linux abstract socket convention). Paths longer than 107 bytes are
truncated.

The caller must `Deallocate` the result (size 110).

### Connect to a Unix socket

```
Socket.ConnectUnix(sock, path)  → Integer (0 = success, error code on failure)
```

Builds a `sockaddr_un` from `path` and calls `connect(sock, addr, 2+strlen(path))`.
The addrlen follows POSIX: `offsetof(sun_path) + strlen(path)`, avoiding the
WSL2 tmpfs bug triggered by +1.

### Bind a Unix socket

```
Socket.BindUnix(sock, path)  → Integer (0 = success, -1 on failure)
```

Unlinks any stale socket file at `path` first (via `unlink(2)`), then calls
`bind(sock, addr, 2+strlen(path))`.

### Listen

```
Socket.Listen(sock, backlog)  → Integer (0 = success, -1 on failure)
```

Calls `listen(sock, backlog)`.

### Accept

```
Socket.Accept(sock)  → Integer (client fd, or -1 on failure)
```

Calls `accept(sock, NULL, NULL)`. Returns a **new fd** for the accepted
connection. The caller must `Socket.Close` the returned fd when done.

---

## LENGTH-PREFIXED MESSAGING

For structured IPC, the library provides a 4-byte big-endian length-prefixed
framing protocol. This is used by HalCode9000's IPC dispatch system.

### Send a message

```
Socket.SendMsg(sock, json_str)  → Integer (bytes sent, or -1)
```

Sends a 4-byte big-endian length header followed by the payload. The length
is the byte count of `json_str` (retrieved via `StringLength`).

Wire format:
```
[byte 0] [byte 1] [byte 2] [byte 3] [payload bytes...]
  MSB                          LSB
```

### Receive a message

```
Socket.RecvMsg(sock)  → Address (String), 0 (disconnect), or -1 (framing error)
```

Reads the 4-byte length header, then reads exactly that many payload bytes.
Returns a freshly allocated null-terminated String. The **caller must free**
the returned string.

If the declared length exceeds **1 MiB** (1,048,576), the library assumes a
framing error: it drains up to 1 MiB from the socket to attempt
resynchronization and returns **-1**.

Returns **0** if the peer disconnected (short read on header or payload).

---

## NON-BLOCKING MODE

```
Socket.SetNonBlock(fd)  → Integer (fcntl result)
```

Calls `fcntl(fd, F_SETFL, O_NONBLOCK)` (syscall 72). After this, `Recv` and
`Send` return immediately with -1 and errno EAGAIN/EWOULDBLOCK if the
operation would block. The caller must implement polling or an event loop.

---

## MEMORY

| Allocation | Size | Freed by |
|-----------|------|----------|
| `CreateAddr` result | 16 bytes | **Caller** (`Deallocate`) |
| `CreateAddrUnix` result | 110 bytes | **Caller** (`Deallocate`) |
| `ParseIPAddress` result | 32 bytes (4×8) | **Caller** (`ArrayDestroy`) |
| `RecvMsg` result | Variable | **Caller** (`Deallocate`) |
| `SetRecvTimeout` timeval | 16 bytes | Internal (freed before return) |
| `SendMsg` header | 4 bytes | Internal (freed before return) |
| `RecvMsg` drain buffer | 4096 bytes | Internal (freed on framing error path) |

Socket fds themselves are kernel resources. `Socket.Close` releases them.

---

## EXAMPLE: IPv4 TCP echo client

```ailang
LibraryImport.Socket
LibraryImport.StringUtils

sock = Socket.Create(SocketConstants.AF_INET, SocketConstants.SOCK_STREAM)
IfCondition LessThan(sock, 0) ThenBlock: {
    StringUtils.PrintString "[Socket] Create failed\n"
    ReturnValue(1)
}

addr = Socket.CreateAddr("127.0.0.1", 8080)
rc = Socket.Connect(sock, addr)
Deallocate addr, 16
IfCondition LessThan(rc, 0) ThenBlock: {
    StringUtils.PrintString "[Socket] Connect failed\n"
    Socket.Close sock
    ReturnValue(1)
}

# Send
msg = "Hello, server!"
Socket.Send sock msg (StringUtils.StringLength msg)

# Receive
buf = Allocate(4096)
n = Socket.Recv sock buf 4095
IfCondition GreaterThan(n, 0) ThenBlock: {
    SetByte buf n 0  # null-terminate
    StringUtils.PrintString buf
}
Deallocate buf, 4096
Socket.Close sock
```

## EXAMPLE: Unix domain IPC server (abstract namespace)

```ailang
LibraryImport.Socket
LibraryImport.StringUtils

sock = Socket.Create(1, SocketConstants.SOCK_STREAM)  # AF_UNIX=1
IfCondition LessThan(sock, 0) ThenBlock: {
    StringUtils.PrintString "[Socket] Create failed\n"
    ReturnValue(1)
}

# Abstract socket (no filesystem inode)
Socket.BindUnix sock "@myapp_ipc"
Socket.Listen sock 128

WhileLoop 1 {
    client = Socket.Accept(sock)
    IfCondition GreaterEqual(client, 0) ThenBlock: {
        msg = Socket.RecvMsg(client)
        IfCondition GreaterThan(msg, 0) ThenBlock: {
            StringUtils.PrintString msg
            Socket.SendMsg client "{\"status\":\"ok\"}"
            Deallocate msg, 0
        }
        Socket.Close client
    }
}
```

## EXAMPLE: Length-prefixed message exchange (client)

```ailang
LibraryImport.Socket
LibraryImport.JSON
LibraryImport.StringUtils

sock = Socket.Create(1, SocketConstants.SOCK_STREAM)
Socket.ConnectUnix sock "@myapp_ipc"

# Build JSON request
JSON.NewObject → req
JSON.SetString req "method" "echo"
JSON.SetString req "payload" "hello"
req_str = JSON.Serialize(req)
Socket.SendMsg sock req_str

# Read JSON response
resp_str = Socket.RecvMsg(sock)
IfCondition GreaterThan(resp_str, 0) ThenBlock: {
    StringUtils.PrintString resp_str
    Deallocate resp_str, 0
}
Deallocate req_str, 0
JSON.Free req
Socket.Close sock
```

---

## SEE ALSO
- `Library.HTTP` — HTTP client that uses `curl` (not Socket) for TLS
- `Library.JSON` — payload format used with `SendMsg`/`RecvMsg`
- `Library.IPCDispatch` — higher-level IPC built on Unix domain sockets
- Linux man pages: `socket(2)`, `connect(2)`, `bind(2)`, `listen(2)`, `accept(2)`, `fcntl(2)`

---

## VERSION
2026-05-16 — rewritten to match actual raw-syscall fd-based implementation

## COPYRIGHT
Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
