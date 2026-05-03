# Library.Socket(ailang)

## NAME
`Library.Socket` — TCP client and server sockets with nonblocking I/O and POSIX async readiness

## SYNOPSIS
```
LibraryImport.Socket
```
> Requires: none (thin over POSIX sockets via AILang FFI)

## DESCRIPTION
Socket provides a direct interface to TCP sockets (AF_INET/AF_INET6, SOCK_STREAM). It supports both client (connect) and server (bind/listen/accept) roles, with nonblocking I/O and edge-triggered readiness notification suitable for integration with event loops.

All operations are synchronous at the call site but the socket may be placed in nonblocking mode where `read` and `write` return immediately with partial results or a would-block indicator.

| Feature | Detail |
|---|---|
| Family | IPv4 (AF_INET) and IPv6 (AF_INET6) |
| Type | SOCK_STREAM (TCP) |
| Nonblocking | Configurable per socket |
| Nagle | Disabled by default (TCP_NODELAY) |
| Reuse | SO_REUSEADDR on listen sockets |
| Backlog | Default 128 |

## FUNCTIONS

### Socket Creation

```
Function.Socket.new
    Input:  —
    Output: Address  (socket handle)
```
Creates a new unconnected TCP socket (AF_INET, SOCK_STREAM). Nagle's algorithm is disabled by default. Returns nil if the OS file descriptor limit is exhausted.

```
Function.Socket.close
    Input:  sock: Address
    Output: —
```
Closes the socket and frees the handle. Safe to call on an already-closed socket.

### Client (Connect)

```
Function.Socket.connect
    Input:  sock: Address, host: Address, port: Integer
    Output: Integer  (0 = success, -1 = error)
```
Resolves `host` (DNS name or IP string) and connects to `port`. Blocks until the connection is established or fails. Returns 0 on success, -1 on error. Use `Socket.lastError` for the error message.

```
Function.Socket.connectNB
    Input:  sock: Address, host: Address, port: Integer
    Output: Integer  (0 = connected, 1 = in-progress, -1 = error)
```
Nonblocking connect. Returns 1 if the connection is in progress (use `pollWrite` to wait for completion). The socket must have been created in nonblocking mode.

### Server (Listen)

```
Function.Socket.bind
    Input:  sock: Address, port: Integer
    Output: Integer  (0 = success, -1 = error)
```
Binds the socket to all interfaces on `port`. Sets SO_REUSEADDR.

```
Function.Socket.listen
    Input:  sock: Address, backlog: Integer
    Output: Integer  (0 = success, -1 = error)
```
Marks the socket as passive. `backlog` is the kernel accept queue depth (default 128, clamped to SOMAXCONN).

```
Function.Socket.accept
    Input:  sock: Address
    Output: Address  (new client socket, or nil)
```
Blocks until a client connects. Returns a new socket handle for the accepted connection, or nil on error. The new socket inherits the nonblocking setting from the listen socket.

```
Function.Socket.acceptNB
    Input:  sock: Address
    Output: Address  (new client socket, or nil if none pending)
```
Nonblocking accept. Returns nil immediately if no connection is pending.

### I/O

```
Function.Socket.read
    Input:  sock: Address, buf: Address, maxLen: Integer
    Output: Integer  (bytes read, 0 = closed, -1 = error)
```
Reads up to `maxLen` bytes into `buf`. In blocking mode, waits for at least one byte (unless the peer closed). In nonblocking mode, returns -1 with EAGAIN/EWOULDBLOCK if no data is available.

```
Function.Socket.write
    Input:  sock: Address, buf: Address, len: Integer
    Output: Integer  (bytes written, -1 = error)
```
Writes `len` bytes from `buf`. May write fewer bytes than requested; the caller must loop to send all data. In nonblocking mode, returns -1 with EAGAIN if the send buffer is full.

```
Function.Socket.readFull
    Input:  sock: Address, buf: Address, len: Integer
    Output: Integer  (0 = success, -1 = error/closed)
```
Convenience: blocks (or loops in nonblocking mode) until exactly `len` bytes are read or the peer closes. Returns 0 on success.

```
Function.Socket.writeFull
    Input:  sock: Address, buf: Address, len: Integer
    Output: Integer  (0 = success, -1 = error)
```
Convenience: loops until all `len` bytes are written. Returns 0 on success.

### Nonblocking Control

```
Function.Socket.setNonblocking
    Input:  sock: Address, enable: Integer
    Output: Integer  (0 = success)
```
Enables (1) or disables (0) nonblocking mode on the socket.

```
Function.Socket.pollRead
    Input:  sock: Address, timeoutMs: Integer
    Output: Integer  (1 = readable, 0 = timeout, -1 = error)
```
Waits up to `timeoutMs` milliseconds for data to become available. timeoutMs=0 polls without blocking; timeoutMs=-1 blocks indefinitely.

```
Function.Socket.pollWrite
    Input:  sock: Address, timeoutMs: Integer
    Output: Integer  (1 = writable, 0 = timeout, -1 = error)
```
Waits for the socket to become writable (useful after a nonblocking connect).

### Info

```
Function.Socket.lastError
    Input:  —
    Output: Address  (String)
```
Returns the last socket error message.

```
Function.Socket.peerAddress
    Input:  sock: Address
    Output: Address  (String: "ip:port")
```
Returns the remote peer address, or nil if not connected.

```
Function.Socket.localAddress
    Input:  sock: Address
    Output: Address
```
Returns the local socket address, or nil if not bound.

## MEMORY

| Allocation | Freed by |
|---|---|
| Socket handle | `close` |
| accept'd socket handle | `close` (caller) |
| Address strings | Internal buffer, reused |

The caller is responsible for providing read/write buffers. Socket does not allocate I/O buffers internally.

## EXAMPLE

```ailang
LibraryImport.Socket
LibraryImport.String

# Client
Socket.new        → sock
Socket.connect    sock  (String.literal "example.com")  80  → rc
Socket.readFull   sock  buf  1024  → _
String.print      buf
Socket.close      sock

# Server (blocking loop)
Socket.new        → server
Socket.bind       server  8080  → _
Socket.listen     server  128   → _
@loop
  Socket.accept   server  → client
  # handle client in a coroutine or fork
  Socket.close    client
  goto @loop
```

## SEE ALSO
`Library.HTTP` — HTTP client built on Socket
`Library.IPCDispatch` — IPC using Unix domain sockets (platform-specific)

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
