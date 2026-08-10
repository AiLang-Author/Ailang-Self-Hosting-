-- CAD product system of record (PostgreSQL) — orthogonal document model
--
-- Design goals:
--   * No proprietary .cadx — interchange lives as typed assets
--   * Documents ≠ revisions + role-tagged assets (open role set)
--   * JSONB for params / feature trees / free meta (add fields without migrations)
--   * Derived caches (STEP, mesh) are assets, not the authority
--
-- Apply:  psql -d cad_db -f CAD/sql/cad_schema.sql
-- Or:     CAD_Repo.InitSchema after ConnectLocal (peer auth as OS user).
--
-- Asset roles (convention, not enum — add new roles without DDL):
--   profile_dxf   authoritative 2D profile (ASCII DXF)
--   hole_dxf      optional through-hole profile
--   step_cache    derived solid interchange
--   feature_tree  JSON feature list (also on cad_revision.feature_tree)
--   plane_tree    future: PlaneFeature coordinate tree JSON
--   face_map      future: persistent face/edge naming map
--   mesh_*        future: tess caches

CREATE TABLE IF NOT EXISTS cad_project (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    meta        JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One product identity (part, assembly, library sketch, …)
CREATE TABLE IF NOT EXISTS cad_document (
    id          BIGSERIAL PRIMARY KEY,
    project_id  BIGINT REFERENCES cad_project(id),
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL DEFAULT 'part',   -- part | assembly | sketch | …
    meta        JSONB NOT NULL DEFAULT '{}',   -- height_mm, units, tags, …
    latest_rev  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cad_document_updated_idx ON cad_document (updated_at DESC);
CREATE INDEX IF NOT EXISTS cad_document_kind_idx ON cad_document (kind);

-- Immutable-ish history: each save is a new revision row
CREATE TABLE IF NOT EXISTS cad_revision (
    id            BIGSERIAL PRIMARY KEY,
    doc_id        BIGINT NOT NULL REFERENCES cad_document(id) ON DELETE CASCADE,
    rev           INTEGER NOT NULL,
    parent_rev    INTEGER,
    message       TEXT NOT NULL DEFAULT '',
    author        TEXT NOT NULL DEFAULT '',
    -- Ordered feature ops / params (extensible without new columns)
    feature_tree  JSONB NOT NULL DEFAULT '[]',
    params        JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doc_id, rev)
);

CREATE INDEX IF NOT EXISTS cad_revision_doc_idx ON cad_revision (doc_id, rev DESC);

-- Role-tagged payloads attached to a revision (orthogonal storage)
CREATE TABLE IF NOT EXISTS cad_asset (
    id            BIGSERIAL PRIMARY KEY,
    rev_id        BIGINT NOT NULL REFERENCES cad_revision(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,              -- open vocabulary (see header)
    media_type    TEXT NOT NULL DEFAULT 'text/plain',
    payload_text  TEXT,                       -- DXF, STEP, JSON, …
    payload_bytea BYTEA,                      -- binary later
    meta          JSONB NOT NULL DEFAULT '{}',
    UNIQUE (rev_id, role)
);

CREATE INDEX IF NOT EXISTS cad_asset_role_idx ON cad_asset (role);

-- Multi-user / agent sessions (product path)
CREATE TABLE IF NOT EXISTS cad_session (
    id          BIGSERIAL PRIMARY KEY,
    user_name   TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at    TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'active',
    meta        JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cad_checkout (
    doc_id      BIGINT PRIMARY KEY REFERENCES cad_document(id) ON DELETE CASCADE,
    session_id  BIGINT REFERENCES cad_session(id),
    owner       TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Normalized feature rows optional for SQL search (not required for open/save)
CREATE TABLE IF NOT EXISTS cad_feature (
    id          BIGSERIAL PRIMARY KEY,
    rev_id      BIGINT NOT NULL REFERENCES cad_revision(id) ON DELETE CASCADE,
    feat_index  INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    params      JSONB NOT NULL DEFAULT '{}',
    suppressed  BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (rev_id, feat_index)
);

INSERT INTO cad_project (name)
VALUES ('default')
ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------------------------
-- Optional one-time migrate from v1 flat cad_part (if present)
-- ------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'cad_part'
  ) THEN
    INSERT INTO cad_document (name, kind, meta, latest_rev)
    SELECT p.name, 'part',
           jsonb_build_object('height_mm', p.height_mm, 'migrated_from', 'cad_part'),
           GREATEST(p.rev, 1)
    FROM cad_part p
    ON CONFLICT (name) DO NOTHING;

    -- Create a revision + assets for migrated parts that have no revisions yet
    INSERT INTO cad_revision (doc_id, rev, message, author, feature_tree, params)
    SELECT d.id, d.latest_rev, 'migrated from cad_part', 'migrate',
           jsonb_build_array(jsonb_build_object('op', 'pad', 'h', p.height_mm)),
           jsonb_build_object('height_mm', p.height_mm)
    FROM cad_document d
    JOIN cad_part p ON p.name = d.name
    WHERE NOT EXISTS (SELECT 1 FROM cad_revision r WHERE r.doc_id = d.id);

    INSERT INTO cad_asset (rev_id, role, media_type, payload_text)
    SELECT r.id, 'profile_dxf', 'application/dxf', p.dxf_text
    FROM cad_revision r
    JOIN cad_document d ON d.id = r.doc_id
    JOIN cad_part p ON p.name = d.name
    WHERE p.dxf_text IS NOT NULL AND p.dxf_text <> ''
    ON CONFLICT (rev_id, role) DO NOTHING;

    INSERT INTO cad_asset (rev_id, role, media_type, payload_text)
    SELECT r.id, 'hole_dxf', 'application/dxf', p.hole_dxf_text
    FROM cad_revision r
    JOIN cad_document d ON d.id = r.doc_id
    JOIN cad_part p ON p.name = d.name
    WHERE p.hole_dxf_text IS NOT NULL AND p.hole_dxf_text <> ''
    ON CONFLICT (rev_id, role) DO NOTHING;

    INSERT INTO cad_asset (rev_id, role, media_type, payload_text)
    SELECT r.id, 'step_cache', 'model/step', p.step_text
    FROM cad_revision r
    JOIN cad_document d ON d.id = r.doc_id
    JOIN cad_part p ON p.name = d.name
    WHERE p.step_text IS NOT NULL AND p.step_text <> ''
    ON CONFLICT (rev_id, role) DO NOTHING;
  END IF;
END $$;
