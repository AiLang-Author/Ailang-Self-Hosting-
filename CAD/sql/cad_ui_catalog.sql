-- CAD UI catalog — single JSONB projection for hosts (IPC tools.json)
-- Apply: psql -d cad_db -f CAD/sql/cad_ui_catalog.sql
-- Kernel: SELECT catalog::text → /tmp/cad_app/tools.json
-- Hosts must not invent cmds beyond this catalog.

CREATE TABLE IF NOT EXISTS cad_ui_catalog (
    role        TEXT PRIMARY KEY,
    catalog     JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default chrome (sketch + feature + solid body ops + construct + view + file)
INSERT INTO cad_ui_catalog (role, catalog) VALUES (
  'default',
  '{
    "schema": 1,
    "app": "cad",
    "role": "default",
    "defaults": {
      "pad_h": 20,
      "shade": "solid",
      "wire": 0,
      "fillet_r": 2,
      "chamfer_d": 2
    },
    "toolbars": [
      {
        "id": "sketch",
        "label": "Sketch",
        "tools": [
          { "id": "line",  "label": "Line",    "cmd": "tool_line",  "group": "draw" },
          { "id": "rect",  "label": "Rect",    "cmd": "tool_rect",  "group": "draw",
            "variants": [
              { "label": "2-Point Rect", "cmd": "tool_rect" },
              { "label": "Center Rect",  "cmd": "tool_rectc" },
              { "label": "3-Point Rect", "cmd": "tool_rect3" }
            ] },
          { "id": "circ",  "label": "Circle",  "cmd": "tool_circ",  "group": "draw",
            "variants": [
              { "label": "Center Radius",  "cmd": "tool_circ" },
              { "label": "2-Point Circle", "cmd": "tool_circ2" },
              { "label": "3-Point Circle", "cmd": "tool_circ3" }
            ] },
          { "id": "arc",   "label": "Arc",     "cmd": "tool_arc3",  "group": "draw",
            "variants": [
              { "label": "3-Point Arc", "cmd": "tool_arc3" },
              { "label": "2-Point Arc", "cmd": "tool_arc2" },
              { "label": "Center Arc",  "cmd": "tool_arc" }
            ] },
          { "id": "poly",  "label": "Polygon", "cmd": "tool_poly6", "group": "draw",
            "variants": [
              { "label": "Slot (2)", "cmd": "tool_poly2" },
              { "label": "Triangle", "cmd": "tool_poly3" },
              { "label": "Square",   "cmd": "tool_poly4" },
              { "label": "Pentagon", "cmd": "tool_poly5" },
              { "label": "Hexagon",  "cmd": "tool_poly6" },
              { "label": "Nonagon",  "cmd": "tool_poly9" }
            ] },
          { "id": "spline","label": "Spline",  "cmd": "tool_spline","group": "draw",
            "variants": [
              { "label": "Control Points", "cmd": "tool_spline" },
              { "label": "Finish Spline",  "cmd": "done" }
            ] },
          { "id": "point",    "label": "Point",    "cmd": "tool_point",  "group": "draw" },
          { "id": "trim",     "label": "Trim",     "cmd": "tool_trim",   "group": "edit" },
          { "id": "fillet2d", "label": "Fillet 2D","cmd": "tool_fillet2d", "group": "edit" },
          { "id": "pick",     "label": "Pick",     "cmd": "tool_pick",   "group": "sel" },
          { "id": "profiles", "label": "Profiles", "cmd": "profiles",    "group": "sel" }
        ]
      },
      {
        "id": "constraint",
        "label": "Constrain",
        "tools": [
          { "id": "fixo",  "label": "Fix to O",    "cmd": "cstr_fixo",  "group": "origin" },
          { "id": "disto", "label": "Dist to O",   "cmd": "cstr_disto", "group": "origin" },
          { "id": "h",     "label": "Horizontal",  "cmd": "cstr_h",     "group": "unary" },
          { "id": "v",     "label": "Vertical",    "cmd": "cstr_v",     "group": "unary" },
          { "id": "rad",   "label": "Radius",      "cmd": "cstr_rad",   "group": "unary" },
          { "id": "coinc", "label": "Coincident",  "cmd": "cstr_coinc", "group": "rel" },
          { "id": "pon",   "label": "On Line",     "cmd": "cstr_pon",   "group": "rel" },
          { "id": "tang",  "label": "Tangent",     "cmd": "cstr_tang",  "group": "rel" },
          { "id": "eqr",   "label": "Equal R",     "cmd": "cstr_eqr",   "group": "rel" },
          { "id": "dist",  "label": "Distance",    "cmd": "cstr_dist",  "group": "rel" },
          { "id": "solve", "label": "Solve",       "cmd": "solve",      "group": "cstr" }
        ]
      },
      {
        "id": "feature",
        "label": "Feature",
        "tools": [
          { "id": "pad",     "label": "Extrude",       "cmd": "repad",   "group": "feat" },
          { "id": "revolve", "label": "Revolve",       "cmd": "revolve", "group": "feat" }
        ]
      },
      {
        "id": "solid",
        "label": "Solid",
        "tools": [
          { "id": "fillet3d",  "label": "Fillet",       "cmd": "tool_fillet3d", "group": "modify",
            "params": [ { "name": "R", "unit": "mm", "default": 5, "cmd_template": "fillet {R}" } ] },
          { "id": "chamfer3d", "label": "Chamfer Body", "cmd": "tool_chamfer", "group": "modify",
            "params": [ { "name": "D", "unit": "mm", "default": 2, "cmd_template": "chamfer {D}" } ] },
          { "id": "wire",      "label": "Wireframe",    "cmd": "wire",      "group": "display" }
        ]
      },
      {
        "id": "construct",
        "label": "Construct",
        "tools": [
          { "id": "plane_xy",  "label": "XY Plane",     "cmd": "plane_xy",     "group": "planes" },
          { "id": "plane_top", "label": "Sketch on Face", "cmd": "plane_top",  "group": "planes" },
          { "id": "plane_off", "label": "Offset Plane", "cmd": "plane_off 20", "group": "planes" },
          { "id": "plane_ang", "label": "Angle Plane",  "cmd": "plane_ang 45", "group": "planes" },
          { "id": "plane_flip","label": "Flip Normal",  "cmd": "plane_flip",   "group": "planes" },
          { "id": "undo",      "label": "Undo",         "cmd": "undo",         "group": "edit" }
        ]
      },
      {
        "id": "view",
        "label": "View",
        "tools": [
          { "id": "mode", "label": "2D/3D", "cmd": "mode", "group": "view" },
          { "id": "grid", "label": "Grid",  "cmd": "grid", "group": "view" }
        ]
      },
      {
        "id": "file",
        "label": "File",
        "tools": [
          { "id": "new",     "label": "New",           "cmd": "newdoc", "group": "file" },
          { "id": "list",    "label": "List Docs",     "cmd": "files",   "group": "file" },
          { "id": "import",  "label": "Import DXF",    "cmd": "import", "group": "file" },
          { "id": "refresh", "label": "Refresh Tools", "cmd": "tools",  "group": "file" }
        ]
      }
    ]
  }'::jsonb
)
ON CONFLICT (role) DO UPDATE SET
  catalog = EXCLUDED.catalog,
  updated_at = now();
