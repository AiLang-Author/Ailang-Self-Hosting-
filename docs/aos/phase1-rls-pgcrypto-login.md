# Phase 1: RLS, pgcrypto, and Login Validation

**Status**: Current Sprint
**Default Credentials**: username=`user`, password=`password`

---

## Overview

This phase establishes the security foundation for AILang OS:

1. PostgreSQL Row-Level Security (RLS) for data isolation
2. pgcrypto extension for bcrypt password hashing
3. Login.ailang validates credentials against PostgreSQL
4. Init re-enables Login gate before launching services

PG data remains pre-packaged in the disk image. No installer flow, no multi-user, no LUKS.

---

## Prerequisite: Fix PG UID Ownership Bug

**Problem**: PostgreSQL refuses to start — reports "wrong owner 94" on `/var/lib/postgresql/data`.

**Root Cause**: Init fork/execs `chown -R 121:124 /var/lib/postgresql/data` but this fails silently. The data directory retains host-build ownership (UID from ext2 image creation).

**Fix**:
- Verify `/bin/chown` exists and is executable in target rootfs
- Add error reporting: check waitpid exit status, print diagnostic if non-zero
- Fallback: use recursive syscall-based chown (walk directory tree with getdents64 + chown syscall 92)
- Alternative: fix ownership during ext2 image creation via Buildroot fakeroot device table

---

## 1. Role Hierarchy

```sql
-- System role: svc_daemon, Init post-bootstrap operations
CREATE ROLE ailang_system_role NOLOGIN;

-- Display server: compositor/window manager (trusted system component)
CREATE ROLE display_server LOGIN IN ROLE ailang_system_role;

-- App sandbox role (parent for all per-user roles)
CREATE ROLE app_user NOLOGIN;

-- Default user role (pre-packaged for base install)
CREATE ROLE user_user LOGIN IN ROLE app_user;
```

**bob** superuser is retained ONLY for Init bootstrap and schema migrations. No application or service connects as bob.

---

## 2. Row-Level Security Policies

### 2.1 Enable RLS

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages ENABLE ROW LEVEL SECURITY;
```

### 2.2 Schema Migration

```sql
ALTER TABLE files ADD COLUMN IF NOT EXISTS owner_role TEXT DEFAULT 'system';
```

### 2.3 Policy Definitions

**users** — user sees own row; admin sees all:
```sql
CREATE POLICY users_self ON users
    FOR ALL TO app_user
    USING (username = replace(current_user, 'user_', '') OR
           (SELECT is_admin FROM users WHERE username = replace(current_user, 'user_', '')));
CREATE POLICY users_system ON users
    FOR ALL TO ailang_system_role
    USING (true);
```

**files** — owner isolation:
```sql
CREATE POLICY files_owner ON files
    FOR ALL TO app_user
    USING (owner_role = replace(current_user, 'user_', '') OR owner_role = 'system');
CREATE POLICY files_system ON files
    FOR ALL TO ailang_system_role
    USING (true);
```

**sessions** — own sessions only:
```sql
CREATE POLICY sessions_own ON sessions
    FOR SELECT TO app_user
    USING (user_id = (SELECT id FROM users WHERE username = replace(current_user, 'user_', '')));
CREATE POLICY sessions_system ON sessions
    FOR ALL TO ailang_system_role
    USING (true);
```

**settings** — app-scoped:
```sql
CREATE POLICY settings_app ON settings
    FOR ALL TO app_user
    USING (app_id = current_setting('app.current_app', true));
CREATE POLICY settings_system ON settings
    FOR ALL TO ailang_system_role
    USING (true);
```

**services, service_status, packages** — read-only for apps:
```sql
CREATE POLICY services_read ON services FOR SELECT TO app_user USING (true);
CREATE POLICY services_system ON services FOR ALL TO ailang_system_role USING (true);

CREATE POLICY service_status_read ON service_status FOR SELECT TO app_user USING (true);
CREATE POLICY service_status_system ON service_status FOR ALL TO ailang_system_role USING (true);

CREATE POLICY packages_read ON packages FOR SELECT TO app_user USING (true);
CREATE POLICY packages_system ON packages FOR ALL TO ailang_system_role USING (true);
```

---

## 3. pgcrypto Password Hashing

### 3.1 Enable Extension

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

The `pgcrypto.so` shared object already exists in the target filesystem at `/usr/lib/postgresql/pgcrypto.so`.

### 3.2 Default User Seed

```sql
INSERT INTO users (username, password_hash, display_name, is_admin, created_at)
    VALUES ('user', crypt('password', gen_salt('bf', 12)), 'User', true, 0)
    ON CONFLICT (username) DO NOTHING;
```

### 3.3 Validation Query

```sql
SELECT id FROM users
    WHERE username = 'user'
    AND password_hash = crypt('password', password_hash);
```

Returns 1 row on match, 0 rows on mismatch. Cost factor 12 = ~250ms per validation (acceptable for login frequency).

---

## 4. Login.ailang Changes

### 4.1 Current State

- `Login_Validate` does hardcoded byte comparison: username="bob", password="ailang"
- No PG connection
- Framebuffer-rendered login dialog with username/password fields

### 4.2 New Validation Flow

Replace `Login_Validate` body:

1. Connect to PG as `bob` (superuser, trust auth) — only for auth query
2. Build query: `SELECT id FROM users WHERE username = '<input>' AND password_hash = crypt('<input>', password_hash)`
3. Execute query via `PG_Query(conn, query)`
4. Check `PG_NumRows(result) > 0`
5. Disconnect
6. Return 1 (success) or 0 (failure)

### 4.3 Security Notes

- Login connects as `bob` superuser because RLS would prevent `user_user` from seeing other users' password_hash
- SQL injection: username/password must be sanitized (escape single quotes)
- Password is zeroed from memory after validation (existing behavior)

---

## 5. Init.ailang Changes

### 5.1 Boot Flow (Phase 1)

```
Mount filesystems
Load boot config, hostname, modules
Network setup
Start SSHD
Init PG data dir (chown fix)
Start PostgreSQL
Wait for PG ready
Create DB + bob user (if needed)
Login_Run()              ← NEW: authentication gate
  → success: continue
  → failure: retry (3 attempts, then halt)
Wait for input devices
Start service daemon
Watchdog loop
```

### 5.2 pg_hba.conf Content Update

Init writes this when creating a fresh PG data dir (initdb path):

```
local all all trust
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
host all all 10.0.2.0/24 trust
```

For the pre-built data dir, pg_hba.conf is baked into schema.sql/build-time config.

Phase 2 upgrade (future): switch app roles to md5 auth.

---

## 6. Service Daemon Connection Change

**Current**: `PG_Connect("127.0.0.1", 5432, "ailang_system", "bob", "")`

**New**: `PG_Connect("127.0.0.1", 5432, "ailang_system", "display_server", "")`

The `display_server` role is a member of `ailang_system_role` and has full access to services/packages tables via RLS policy.

---

## 7. IPC App User Context

When the display server launches an IPC app (via fork/exec from service daemon or deskbar click):

1. Set environment: `PGUSER=user_user`, `PGDATABASE=ailang_system`, `PGHOST=127.0.0.1`
2. App reads `PGUSER` from environment and connects to PG using that role
3. RLS policies enforce data isolation automatically

---

## 8. Files to Modify

| File | Changes |
|------|---------|
| `rootfs_overlay/system/schema.sql` | Add `CREATE EXTENSION pgcrypto`, role creation, RLS policies, `owner_role` column, default user with bcrypt hash |
| `OS/Init.ailang` | Fix chown error handling, re-enable `Login_Run()` call after PG ready, update pg_hba.conf content |
| `OS/Login.ailang` | Replace `Login_Validate` with PG bcrypt query, change default credentials to user/password |
| `OS/Schema.ailang` | Add role creation + RLS DDL (mirrors schema.sql for runtime path) |
| `OS/ServiceDaemon.ailang` | Change PG connection role from `bob` to `display_server` |

---

## 9. Verification

| Test | Expected |
|------|----------|
| Boot system | PG starts without ownership error |
| Login with `user` / `password` | Success, desktop loads |
| Login with wrong password | Rejection, retry prompt |
| 3 wrong attempts | System halts |
| `psql -U user_user -d ailang_system -c "SELECT * FROM files"` | Only sees own files + system files |
| `psql -U display_server -d ailang_system -c "SELECT * FROM services"` | Full access |
| `psql -U user_user -d ailang_system -c "DELETE FROM services"` | Permission denied |
