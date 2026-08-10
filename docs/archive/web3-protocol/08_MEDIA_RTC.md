# 08 — Media & WebRTC: Buffer Streams, Surface Contracts, and DRM Policy

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Media Philosophy in Web 3.0

Web 3.0 explicitly separates the **User Interface** (deterministic, server-owned, vector-first) from **Media Payloads** (high-bandwidth, continuous, opaque audio/video). 

The Web 3.0 protocol does not attempt to reinvent video codecs or streaming protocols. Instead, it provides a **pure client buffer stream contract**. Existing technologies (WebRTC, HLS, DASH, raw RTP) operate exactly as they do now. Web 3.0 simply provides the signaling channel to initiate the streams and the display surface to render them.

### 1.1 The DRM Policy

**Web 3.0 implements zero client-side DRM.** 

Digital Rights Management (DRM) on the consumer client is fundamentally a flawed abstraction. Since hardware-level capture (e.g., HDMI splitters, loopback audio interfaces, screen recording) can capture any rendered pixels and audio, client-side DRM serves only to bloat the client and punish legitimate usage. 

In Web 3.0, DRM is considered strictly a **server-side concern**:
- If a client lacks authorization to view a stream, the server simply *does not send the stream*.
- Server-side access tokens and ephemeral URLs are used for stream authentication.
- No obfuscated binary blobs, no Encrypted Media Extensions (EME).

---

## 2. The Client Buffer Stream Contract

Media integration relies on three concepts:
1. **Signaling:** Using the Web 3.0 IPC channel (JSON Events/Updates) to negotiate the stream.
2. **Resource Allocation:** Registering the stream as a TVG resource (`RES_STREAM`).
3. **Surface Mapping:** Assigning the stream resource to a specific scene-graph node (`MEDIA_SURFACE`).

Once established, the client OS or native media subsystem decodes the raw bytes and paints them to the bounded TVG surface. The server can draw TVG UI (custom player controls, chat overlays) directly on top of this surface.

---

## 3. TVG Protocol Extensions for Media

To support the buffer contract, the TinyVG subset is extended with one new resource type and one new scene-graph node type.

### 3.1 RES_STREAM (0x54)

Registers an external media stream buffer.

```
[u8: 0x54] [varuint: resource_id] [u8: stream_type] [string: uri_or_config]
```

| Stream Type | Description | URI/Config Format |
|-------------|-------------|-------------------|
| 0x00 | HTTP Stream | HLS / DASH / MP4 URL |
| 0x01 | Raw TCP/UDP | `<ip>:<port>:<protocol>` |
| 0x02 | WebRTC | Client-local UUID mapped to WebRTC session |
| 0x03 | Local Device| `device://camera:0` or `device://mic:0` |

### 3.2 SG_NODE_CREATE: MEDIA_SURFACE (Type 0x07)

Creates a scene graph node that acts as a rendering plane for a `RES_STREAM`.

```
[u8: 0x10] [varuint: node_id] [u8: 0x07] [varuint: parent_id]
           [varuint: stream_resource_id]
```

Like any other TVG node, the `MEDIA_SURFACE` can be moved, scaled, rotated, or hidden using standard `SG_TRANSFORM`, `LAYOUT_SET`, and `SG_VISIBLE` commands.

---

## 4. WebRTC Encapsulation

WebRTC handles peer-to-real-time media, but requires a signaling channel to negotiate connections. Web 3.0 handles signaling natively through its existing `EVENT` and `UPDATE` frames.

### 4.1 Signaling Flow

```
CLIENT                                              SERVER
  │                                                   │
  │ 1. User clicks "Join Call"                        │
  │── EVENT (action: "webrtc:join") ─────────────────►│
  │                                                   │
  │ 2. Server creates WebRTC session, sends Offer     │
  │◄── UPDATE (commands: [RES_STREAM], config: Offer)─│
  │                                                   │
  │ 3. Client native WebRTC processes Offer           │
  │    Client generates Answer + ICE candidates       │
  │── EVENT (action: "webrtc:answer", payload: SDP) ─►│
  │                                                   │
  │ 4. Direct WebRTC Media flow begins (Out of band)  │
  │◄════════════ UDP / RTP Stream ═══════════════════►│
  │                                                   │
  │ 5. Client paints decoded frames to MEDIA_SURFACE  │
```

### 4.2 Markup for WebRTC

The server defines the media layout in HTML, mapping interactions to signaling actions.

```html
<region id="video-conference">
  <div we-vector="true" id="remote-video-container">
    <!-- Server will send TVG commands to create a MEDIA_SURFACE here -->
  </div>
  <div class="controls">
    <!-- Web 3.0 custom UI replaces standard HTML video controls -->
    <button we-action="webrtc:toggle-mute">Mute</button>
    <button we-action="webrtc:hangup">Leave</button>
  </div>
</region>
```

### 4.3 Signaling Payload Example

When the server wants to start a WebRTC stream, it sends an UPDATE with the SDP payload and creates the TVG resources:

```json
{
  "type": "update",
  "seq": 200,
  "region": "video-conference",
  "commands": [
    // 1. Client handles the WebRTC SDP offer using its native stack
    {"op": "webrtc_offer", "session_id": "rtc-1", "sdp": "v=0\r\no=- 4611..."},
    
    // 2. Register the WebRTC session as a TVG stream resource (Type 0x02)
    {"op": "res_stream", "id": 10, "type": 2, "config": "rtc-1"},
    
    // 3. Create the display surface attached to the stream
    {"op": "node_create", "id": 50, "type": 7, "parent": 1, "stream_id": 10},
    
    // 4. Position the video surface on screen
    {"op": "layout_set", "node": 50, "x": 0, "y": 0, "w": 1280, "h": 720}
  ]
}
```

The client responds with its SDP answer via a standard EVENT:

```json
{
  "action": "webrtc:answer",
  "payload": {
    "session_id": "rtc-1",
    "sdp": "v=0\r\no=- 8762..."
  },
  "seq": 45
}
```

---

## 5. Standard Media Streaming (HLS / DASH / MP4)

For non-interactive video (e.g., Netflix, YouTube equivalents), the encapsulation is even simpler. The server assigns an HTTP stream URL directly to the resource.

### 5.1 Playback Initiation

```json
{
  "type": "update",
  "seq": 310,
  "commands": [
    // Register HTTP stream resource (Type 0x00)
    {"op": "res_stream", "id": 11, "type": 0, "config": "https://media.server/movie.m3u8"},
    
    // Create display surface
    {"op": "node_create", "id": 51, "type": 7, "parent": 1, "stream_id": 11}
  ]
}
```

### 5.2 Server-Owned Playback Controls

Because the client provides no `<video>` element or native browser controls, the server dictates the UI.

- **Play/Pause:** User clicks a Web 3.0 button → EVENT sent to server → Server sends an UPDATE with an `op: stream_control` command to pause the buffer.
- **Seeking:** User drags a Web 3.0 slider → EVENT sent to server → Server sends an `op: stream_seek` command.
- **Subtitles:** Server pushes TVG `TEXT` updates directly over the `MEDIA_SURFACE` node based on the current playback timestamp.

---

## 6. Client Hardware Device Access

Capturing local media (Webcam / Microphone) follows the same pattern. The client provides no JavaScript `getUserMedia()` API. 

Instead, the user selects a device via the server-rendered UI. The server explicitly requests the client to map a local device to a stream resource:

```json
{"op": "res_stream", "id": 12, "type": 3, "config": "device://camera:0"}
```

The client OS handles the hardware permission prompt ("Allow Camera Access?"). Once granted, the stream buffer can be used locally in a `MEDIA_SURFACE` (for a preview mirror) and bound to a WebRTC session to transmit to the server.