# Erdstall Admin

A local desktop application for processing 3D `.ply` cave, tunnel, and Erdstall scans.

Erdstall Admin lets you import a mesh or point cloud, repair it, detect patches, add path points, calculate a cave path, and export the final model as `.glb` for web or mobile use.

The app runs locally on your computer. It does not require Django, a server, or an internet connection after setup.

---

## Features

- Local project-based workflow
- Import `.ply` meshes and `.ply` point clouds
- Optional texture folder import
- Point cloud to mesh conversion
- Mesh repair and cleanup
- Optional Screened Poisson Reconstruction
- Selective hole filling for cave/tunnel scans
- Patch detection and patch export
- Path point import from MeshLab `.pp` files
- Path calculation through the cave mesh
- Final mesh and mobile mesh output
- GLB export with optional human scale model
- Dark desktop GUI built with PySide6
- Cross-platform support for Windows, macOS, and Linux

---

## Recommended workflow

### Mesh input

```text
Add New Project
↓
Fill Holes
↓
Detect Patches
↓
Add Path Points
↓
Calculate Path
↓
Convert GLB
```

### Point cloud input

```text
Add New Project
↓
Convert Point Cloud to Mesh
↓
Fill Holes
↓
Detect Patches
↓
Add Path Points
↓
Calculate Path
↓
Convert GLB
```

---

## Project structure

After processing a project, the folder usually looks like this:

```text
erdstall_admin/
├─ data/
│  ├─ ply/
│  │  └─ ERDSTALL_001/
│  │     ├─ original.ply
│  │     ├─ repaired_mesh.ply
│  │     ├─ mesh.ply
│  │     ├─ mesh_mobile.ply
│  │     ├─ mesh.glb
│  │     ├─ patches.json
│  │     ├─ path_points.csv
│  │     ├─ path.csv
│  │     ├─ path.json
│  │     ├─ mesh/
│  │     │  └─ texture files
│  │     ├─ textures_backup/
│  │     └─ patches/
│  │        ├─ patch_0.ply
│  │        └─ ...
│  └─ _path_tmp/
├─ erdstall_admin_gui/
├─ erdstall_pipeline/
├─ public/
│  ├─ admin_icon.png
│  ├─ Logo.png
│  └─ person.glb
├─ main.py
├─ requirements.txt
└─ README.md
```

> Note: texture files are currently stored in the project folder named `mesh/`. This is the current internal project convention.

---

## Requirements

You need:

- Python 3.10 or 3.11
- Java 17 or newer
- Fiji / ImageJ for path calculation
- Enough RAM for large `.ply` files
- Visual Studio Code, optional but recommended

Large cave scans can be heavy. Files between `500 MB` and `1 GB` may take a long time depending on CPU speed, RAM, and mesh density.

---

# Installation

## Windows

Install Python 3.11:

```bash
winget install Python.Python.3.11
py -3.11 --version
```

Install Java 17:

```bash
winget install EclipseAdoptium.Temurin.17.JDK
java -version
```

Optional: install Visual Studio Code:

```bash
winget install Microsoft.VisualStudioCode
```

Create and activate a virtual environment:

```bash
py -3.11 -m venv .venv311
.venv311\Scripts\activate
pip install -r requirements.txt
```

---

## macOS

Install Homebrew if needed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python 3.11:

```bash
brew install python@3.11
python3.11 --version
```

Install Java 17:

```bash
brew install openjdk@17
```

For Apple Silicon Macs:

```bash
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
```

For Intel Macs:

```bash
echo 'export PATH="/usr/local/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
```

Reload your terminal and check Java:

```bash
source ~/.zshrc
java -version
```

Optional: install Visual Studio Code:

```bash
brew install --cask visual-studio-code
```

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Linux

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip openjdk-17-jdk
python3 --version
java -version
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

# Fiji / ImageJ setup

Fiji is required for the **Calculate Path** step.

Download Fiji from:

```text
https://imagej.net/software/fiji/downloads
```

Then open Erdstall Admin and go to:

```text
Setup → Browse → Save → Validate setup
```

Select the Fiji executable:

## Windows

Select one of these, depending on your Fiji installation:

```text
Fiji.app/ImageJ-win64.exe
Fiji.app/fiji-windows-x64.exe
```

## macOS

Select:

```text
Fiji.app
```

The app resolves the executable inside the `.app` folder.

## Linux

Select:

```text
Fiji.app/ImageJ-linux64
```

On Linux, make sure the file has execute permission.

---

# Running the app

Start the desktop application with:

```bash
python main.py
```

On Windows, this also works:

```bash
py main.py
```

---

# Using the app

## 1. Create a project

Click:

```text
Add New
```

Select:

- Project name, for example `ERDSTALL_001`
- A `.ply` mesh or point cloud file
- Optional texture folder

The source file is copied into the project as:

```text
original.ply
```

The project is created inside:

```text
data/ply/PROJECT_NAME/
```

---

## 2. Select a project

Projects are listed on the left side.

Click a project to make it active.

The dashboard shows whether these files are available:

- Original mesh
- Repaired mesh
- Final mesh
- Mobile mesh
- Patches folder
- Textures folder
- Texture backup
- Path JSON
- Path points CSV

---

## 3. Convert point cloud to mesh

If `original.ply` is detected as a point cloud, the app shows:

```text
Convert Point Cloud to Mesh
```

Use this before Fill Holes.

Output:

```text
repaired_mesh.ply
```

---

## 4. Fill holes and repair mesh

Click:

```text
Fill Holes
```

Available modes:

```text
No filling / cleanup only
Normal hole filling only
Poisson reconstruction only
Poisson + normal hole filling
```

This step can:

- Clean duplicate faces and vertices
- Repair non-manifold geometry
- Keep the largest connected component
- Fill holes below the selected top cutoff
- Smooth the mesh
- Transfer texture colors to vertex colors
- Reduce mesh size

Outputs:

```text
repaired_mesh.ply
mesh.ply
mesh_mobile.ply
```

---

## 5. Detect patches

Click:

```text
Detect Patches
```

This compares the repaired mesh with the original mesh and exports patch components.

Outputs:

```text
patches/
patches.json
```

---

## 6. Add path points

Click:

```text
Add Path Points
```

Select a MeshLab `.pp` picked-points file.

The app expects at least 6 points:

```text
first 3 points  → averaged into the start point
next 3 points   → averaged into the end point
```

Output:

```text
path_points.csv
```

---

## 7. Calculate path

Click:

```text
Calculate Path
```

Required files:

```text
mesh.ply
path_points.csv
```

This step:

1. Copies the final mesh and path points to a temporary folder
2. Reduces the mesh for path finding
3. Converts the mesh to a raw voxel volume
4. Runs Fiji / ImageJ skeletonization
5. Merges skeleton and volume data
6. Computes the path
7. Copies the final CSV and JSON back to the project folder

Outputs:

```text
path.csv
path.json
```

---

## 8. Export GLB

Click:

```text
Convert GLB
```

This exports:

```text
mesh.ply
```

to:

```text
mesh.glb
```

The export can also add a human scale reference model from:

```text
public/person.glb
```

You can configure:

- Human model on/off
- Human height
- Floor offset
- Human up axis
- Export rotation

---

# Output files explained

## `original.ply`

The imported source file. This can be a mesh or a point cloud.

## `repaired_mesh.ply`

The repaired or reconstructed mesh.

## `mesh.ply`

The final cleaned mesh used for later steps.

## `mesh_mobile.ply`

A lighter version of the final mesh for mobile or web use.

## `mesh.glb`

The final GLB export.

## `patches.json`

Metadata for detected patches.

## `patches/`

Folder containing exported patch meshes.

## `path_points.csv`

The selected start and end path points.

## `path.csv`

The calculated path as CSV.

## `path.json`

The calculated path as JSON.

## `mesh/`

Imported texture files.

## `textures_backup/`

Backup of original texture files.

---

# Notes for cave and tunnel scans

Cave scans are difficult data.

They often contain:

- Missing walls
- Open surfaces
- Noisy point clouds
- Floating fragments
- Large holes
- Thin geometry
- Uneven scan density
- Difficult texture data

There is no single perfect setting for every scan. Always inspect the result after each major step.

---

## Screened Poisson Reconstruction

Screened Poisson Reconstruction can be useful for point clouds and broken meshes, but it can also create problems in cave scans.

Possible issues:

- Blobby surfaces
- Closed tunnel openings
- Lost interior details
- Over-smoothed walls
- Extra surfaces in empty areas
- High memory usage

Recommended approach:

- Start with conservative settings
- Avoid very high depth values unless the input is clean and dense
- Remove floating noise before reconstruction when possible
- Keep a backup of the original scan
- Compare repaired results with the original scan

---

# Tips

## If the model is too noisy

Try:

- Cleaning the source scan before import
- Lowering reconstruction depth
- Increasing point cloud downsampling
- Removing small floating components
- Running patch detection
- Checking the original scan density

## If the model is too smooth or blobby

Try:

- Lowering smoothing iterations
- Avoiding Poisson reconstruction for already usable meshes
- Lowering Poisson depth
- Reducing aggressive hole filling
- Checking point cloud normals

## If tunnels get closed

Try:

- Using cleanup or normal filling instead of Poisson
- Lowering hole filling strength
- Increasing the ignored top percentage in Fill Holes
- Checking whether the opening is detected as a hole
- Using a cleaner input mesh

---

# Troubleshooting

## No projects are shown

Click:

```text
Refresh
```

Also check that project folders exist inside:

```text
data/ply/
```

## Fill Holes is disabled

For mesh projects, the app needs:

```text
original.ply
```

For point cloud projects, run:

```text
Convert Point Cloud to Mesh
```

first.

## Convert Point Cloud to Mesh is missing

The button only appears when `original.ply` has no faces and is detected as a point cloud.

## Calculate Path is disabled

The app needs both:

```text
mesh.ply
path_points.csv
```

Run Fill Holes and Add Path Points first.

## GLB export says `mesh.ply` is missing

Run Fill Holes first. The GLB exporter uses:

```text
mesh.ply
```

## Fiji validation fails

Check:

- Fiji is installed
- Java 17 or newer is installed
- The selected Fiji path is correct
- On macOS, select `Fiji.app`
- On Linux, the Fiji executable has execute permission

## Path calculation fails

Check:

- `mesh.ply` exists
- `path_points.csv` exists
- Fiji validation passes
- Start and end points are inside or near the cave mesh
- The mesh is not too broken or too sparse
- The generated skeleton is not empty

## Processing is very slow

Try:

- Use a smaller test scan first
- Reduce point cloud size
- Lower Poisson depth
- Close other memory-heavy apps
- Use a computer with more RAM
- Avoid Poisson reconstruction on already usable meshes

---

# Development notes

Main entry point:

```text
main.py
```

Main GUI files:

```text
erdstall_admin_gui/windows/main_window.py
erdstall_admin_gui/windows/home_page.py
```

Pipeline code:

```text
erdstall_pipeline/
```

Settings classes:

```text
erdstall_pipeline/settings/
```

Worker classes:

```text
erdstall_admin_gui/workers/
```

The GUI uses `QThread` workers so long processing tasks do not freeze the interface.

---

# Configuration

Main constants are stored in:

```text
erdstall_pipeline/config.py
```

Important values:

```python
DATA_DIR = BASE_DIR / "data"
PLY_DIR = DATA_DIR / "ply"
WORK_DIRNAME = "_path_tmp"

ORIGINAL_MESH = "original.ply"
REPAIRED_MESH = "repaired_mesh.ply"
FINAL_MESH = "mesh.ply"

PATH_POINTS_FILENAME = "path_points.csv"
PATH_OUTPUT_FILENAME = "path.csv"
PATH_JSON_FILENAME = "path.json"

SIZE = 180
```

---

# Safety notes

Always keep a backup of the original scan.

The app may overwrite generated files such as:

```text
repaired_mesh.ply
mesh.ply
mesh_mobile.ply
mesh.glb
patches.json
path.csv
path.json
```

Do not use generated files as your only copy of the scan.

---

# License

Add your license here.

Example:

```text
MIT License
```

---

# Author

Erdstall Admin Local Pipeline
