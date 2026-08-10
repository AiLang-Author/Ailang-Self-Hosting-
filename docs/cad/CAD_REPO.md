# CAD.Repo — PostgreSQL system of record

**Status:** orthogonal v2 (document / revision / asset)  
**Driver:** `LibraryImport.PostgreSQL_Complete` (wire protocol v3, Unix peer + TCP)  
**No `.cadx`.** Interchange and authority live in SQL + typed assets.

---

## Why orthogonal

Hardcoding `dxf_text` / `step_text` columns locks every new payload into a migration.
Instead:

| Table | Role |
|-------|------|
| `cad_document` | Stable identity: name, kind, **meta JSONB**, `latest_rev` |
| `cad_revision` | History: `feature_tree` JSONB, `params` JSONB, message, author |
| `cad_asset` | **Role-tagged** payloads on a revision (open vocabulary) |
| `cad_feature` | Optional normalized feature rows for SQL search |
| `cad_session` / `cad_checkout` | Multi-user / agent product path |

**New capability ⇒ new asset `role` or JSON key, not a new table.**

### Asset roles (convention)

| Role | Media | Authority |
|------|--------|-----------|
| `profile_dxf` | `application/dxf` | **Authoritative** 2D profile |
| `hole_dxf` | `application/dxf` | Optional through-hole profile |
| `step_cache` | `model/step` | Derived solid cache |
| `plane_tree` | `application/json` | *(planned)* PlaneFeature stack |
| `face_map` | `application/json` | *(planned)* persistent face/edge names |
| `mesh_*` | binary later | Tess caches |

---

## Driver confirmation

```ailang
LibraryImport.PostgreSQL_Complete   // PG_Connect / PG_ConnectUnix / PG_Query / …
LibraryImport.Cad.CAD_Repo
```

`CAD_Repo.ConnectLocal` → peer auth as OS user `bob`, database `cad_db`.

---

## API surface (product)

| Function | Meaning |
|----------|---------|
| `ConnectLocal` / `Disconnect` | PG session |
| `InitSchema` | Create orthogonal tables (idempotent) |
| `SavePart(name, sketch, solid, H, hole)` | New revision + assets |
| `LoadPart` / `LoadPartRev` | Rebuild solid from DXF assets |
| `ListParts` / `ListRevisions` | Discovery |
| `SetLastMessage` | Commit message on latest rev |
| `PutAssetText` / `FetchAssetToFile` | Extensible blob path |
| `BeginSession` / `EndSession` | Session bookkeeping |

CLI / app:

```bash
createdb cad_db
psql -d cad_db -f CAD/sql/cad_schema.sql   # full DDL + migrate from old cad_part

./cad_app.x --headless -i diamond.dxf -H 15 --name mypart --save
./cad_app.x --headless --load --name mypart -o out.bmp
# live: --name mypart → keys p=save g=load
```

Smoke: `./CAD/smoke_app.sh` (runs `test_repo_live` when `cad_db` is reachable).

---

## Roadmap (storage stays orthogonal)

1. **List / open UI** — `ListParts` + pick name in host  
2. **Revision browser** — `ListRevisions` + load rev N  
3. **Richer feature_tree** — pad/cut/fillet ops as JSON; `cad_feature` rows  
4. **Checkout** — `cad_checkout` enforce single writer  
5. **Planes** — `plane_tree` asset (`plane_coordinate_tree_spec.md`)  
6. **Topo naming** — `face_map` asset + `CAD_Feat.ResolveNaming` (design § Feat_Pid)

Regeneration rule remains: **sketch / feature_tree authority → rebuild solid**; STEP is cache.

---

## Schema file

`CAD/sql/cad_schema.sql` — full DDL, indexes, optional migrate from v1 `cad_part`.
