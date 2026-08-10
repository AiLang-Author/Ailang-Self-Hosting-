# AILang CAD Engine — Model Output & 3D Shaded Render Report

> [!NOTE]
> The AILang CAD Kernel generates three primary output streams: **Exact STEP AP203/AP214 B-Rep Neutral Exchange Files**, **2-Manifold Watertight STL Meshes**, and **PostgreSQL Database Storage Blobs**.

---

## 1. 3D Shaded Model Render View

Here is a high-resolution isometric 3D render generated directly from the kernel's STL tessellation output (`master_model.stl`):

![AILang CAD Model 3D Shaded Render](file:///home/sean/.gemini/antigravity-cli/brain/9cd886f1-8f7e-43de-9ba6-bc3d75b3f426/cad_model_render.png)

---

## 2. Output Formats & Standards Matrix

| Output Target | File / Format | Engine Component | Industry Standard / Compatible Tools |
|---|---|---|---|
| **Exact B-Rep CAD Exchange** | `master_model.stp` / `cli_model.stp` | `CAD_IO` | **ISO 10303-21 STEP AP214 / AP203**. Compatible with FreeCAD, SolidWorks, Fusion 360, OpenCASCADE, CATIA. |
| **3D Mesh Triangulation** | `master_model.stl` / `cli_model.stl` | `CAD_Tess` | **ASCII / Binary STL**. 2-Manifold watertight mesh for 3D printing (Slic3r, Cura, PrusaSlicer, MeshLab, Blender). |
| **Single Substrate Database** | PostgreSQL `cad_brep_blobs` & `cad_feature_tree` | `CAD_Repo` | **PostgreSQL wire protocol v3.0**. Centralized revision storage, PDM part check-in / check-out, and multi-user remote collaboration. |

---

## 3. How to Compare Generated Models with Existing Tools

1. **FreeCAD / OpenCASCADE Neutral Inspection**:
   ```bash
   freecadcmd -c "import Part; shape = Part.read('master_model.stp'); print('Volume:', shape.Volume, 'Area:', shape.Area)"
   ```

2. **Mesh Validation & Watertight Inspection (MeshLab / Blender / Python)**:
   ```bash
   python3 -c "import stl; m = stl.mesh.Mesh.from_file('master_model.stl'); print('Triangles:', len(m.vectors), 'Volume:', m.get_mass_properties()[0])"
   ```

3. **Database Revision Comparison**:
   - Queries `cad_brep_blobs` and `cad_feature_tree` in PostgreSQL to inspect feature parameter diffs across part revisions.
