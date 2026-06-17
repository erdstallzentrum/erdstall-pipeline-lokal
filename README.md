# Erdstall Pipeline Local

A local desktop tool for preparing Erdstall / cave `.ply` scans for web use.

The app can import a `.ply` mesh or point cloud, repair and clean it, create a lighter mobile mesh, calculate a path with Fiji / ImageJ, export `.glb` files, create XML metadata, and adjust texture images.

---

## Typical output

Each project is stored in:

```text
data/ply/PROJECT_NAME/
```

Important files:

```text
original.ply        imported source file
converted.ply       point-cloud-to-mesh result, only for point cloud projects
repaired_mesh.ply   repaired / reconstructed mesh
mesh.ply            final main mesh
mesh_mobile.ply     reduced mobile mesh
mesh.glb            main GLB export
mesh_mobile.glb     mobile GLB export
path_points.csv     start/end points for path calculation
path.csv            calculated path as CSV
path.json           calculated path as JSON
metadata.xml        XML metadata
mesh/               texture folder
textures_backup/    texture backup
```

---

# Installation

## macOS, recommended setup

### 1. Install Fiji / ImageJ

Download Fiji:

```text
https://imagej.net/software/fiji/downloads
```

Move it to:

```text
/Applications/Fiji.app
```

On macOS, `Fiji.app` is an app folder. The real executable is usually:

```text
/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx
```

In the Erdstall app, select the `Fiji.app` folder in `Setup`. The app resolves the real executable automatically.

If validation says the file is not executable, run:

```bash
chmod +x "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx"
```

### 2. Run the setup script

Open Terminal in the project folder:

```bash
chmod +x start_mac.sh
./start_mac.sh
```

The script prepares Homebrew, Python 3.11, OpenJDK 17, Node.js, npm packages, the Python virtual environment, and starts the GUI.

### 3. Validate Fiji in the app

Open:

```text
Setup → Browse → select /Applications/Fiji.app → Save → Validate setup
```

Do this before using `Calculate Path`.

### 4. Start the app later

Either run:

```bash
./start_mac.sh
```

or manually:

```bash
source .venv/bin/activate
python -m erdstall_admin_gui.main
```

---

## Windows setup

Download and extract Fiji, for example to:

```text
C:\Fiji.app\
```

In the app setup, select one of these files:

```text
C:\Fiji.app\ImageJ-win64.exe
C:\Fiji.app\fiji-windows-x64.exe
```

Run PowerShell in the project folder:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start_windows.ps1
```

Start manually later with:

```powershell
.\.venv\Scripts\Activate.ps1
python -m erdstall_admin_gui.main
```

---

## Linux setup

Install system packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip openjdk-17-jdk nodejs npm
```

Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm install
```

Select the Fiji executable in `Setup`, usually:

```text
Fiji.app/ImageJ-linux64
```

If needed:

```bash
chmod +x Fiji.app/ImageJ-linux64
```

Start the app:

```bash
python -m erdstall_admin_gui.main
```

---

# Usage guide

## 1. Create a project

Click:

```text
Add New
```

Choose:

- project name
- `.ply` mesh or `.ply` point cloud file
- optional texture folder

The app copies the source file into the project as:

```text
original.ply
```

---

## 2. Select the project

Projects are shown on the left side.

Click a project to make it active. The `Project Overview` shows which files are available or missing.

---

## 3. Recommended workflow

### For mesh input

```text
Add New
→ Fill Holes
→ Add Path Points
→ Calculate Path
→ Convert GLB
→ Create XML metadata, optional
```

### For point cloud input

```text
Add New
→ Convert Point Cloud to Mesh
→ Fill Holes
→ Add Path Points
→ Calculate Path
→ Convert GLB
→ Create XML metadata, optional
```

---

# Convert Point Cloud to Mesh

Use this step only when the imported `.ply` file is a point cloud and not already a triangle mesh.

Click:

```text
Convert Point Cloud to Mesh
```

The output is:

```text
converted.ply
```

After this step, continue with:

```text
Fill Holes
```

## Recommended start setting

For most Erdstall / cave point clouds, start with:

```text
Mode: Ball Pivoting
```

Only switch to `Poisson` if Ball Pivoting creates too many holes, broken surfaces, or disconnected pieces.

---

## Reconstruction Mode

### Mode

Choose how the point cloud should become a mesh.

```text
Ball Pivoting
```

Best first choice for cave scans. It tries to create triangles between nearby points. It usually keeps the scan shape more realistic and avoids closing large openings too aggressively.

Use it when:

- the point cloud is already dense
- you want to preserve cave/tunnel shape
- you want a mesh that follows the scan closely
- Poisson makes the cave look too inflated or too smooth

```text
Poisson
```

Creates a new continuous surface from the point cloud normals. It can repair messy point clouds better, but it may smooth details or close areas that should stay open.

Use it when:

- Ball Pivoting leaves too many holes
- the scan is noisy or incomplete
- you need a more closed, continuous surface
- the result does not need to preserve every small rough detail

---

## Cave / Ball Pivoting Options

These settings are visible when `Mode` is set to `Ball Pivoting`.

### Ball radius factor 1 / 2 / 3 / 4

These control the ball sizes used by the Ball Pivoting reconstruction.

The app first estimates the average distance between points. Each radius factor is multiplied by that spacing. Smaller values create tighter, more detailed triangles. Larger values can bridge wider gaps.

Default values:

```text
1.1, 1.8, 3.0, 5.0
```

When to change:

- If the mesh has many small holes, slightly increase the larger values, for example `3.0 → 4.0` or `5.0 → 6.0`.
- If the mesh creates false bridges across openings, lower the larger values.
- If fine details disappear, lower the smaller values.
- If the mesh is too fragmented, increase the middle and large values.

Good rule:

```text
Smaller radii = more detail, more holes
Larger radii  = fewer holes, more risk of false surfaces
```

### Remove small components

Removes small disconnected mesh islands after reconstruction.

Keep this enabled for most scans. It removes floating fragments caused by noise, dust, isolated scan points, or small broken parts.

Turn it off only if the scan contains real separate parts that must stay in the final model.

### Min component ratio

Controls how small a disconnected piece must be before it is removed.

The value is relative to the largest connected mesh component.

Default:

```text
0.0005
```

When to change:

- Increase it if many small floating pieces remain.
- Decrease it if real small side passages or details are removed.
- Keep it low for complex cave scans where small connected-looking parts may still be important.

Example:

```text
0.0005 = very conservative cleanup
0.005  = stronger cleanup
```

### Fill small holes

Enables small-hole filling directly after Ball Pivoting.

For the current workflow, this should usually stay off because the separate `Fill Holes` step gives more control.

Turn it on only if the Ball Pivoting result has many small simple holes and you want to fix them immediately.

### Max hole size

Only active when `Fill small holes` is enabled.

It limits how large a hole may be for automatic filling.

When to change:

- Increase it if small holes are not being filled.
- Decrease it if entrances, shafts, or real openings are being closed.
- Keep it conservative if the cave has many intentional openings.

---

## Preprocessing

### Downsample voxel size

Reduces the number of points before meshing by merging nearby points into voxels.

Default:

```text
0.005
```

What it does:

- makes processing faster
- reduces noise
- lowers memory usage
- can remove very fine details if set too high

When to change:

- Increase it for very large or noisy point clouds.
- Decrease it if the result loses too much detail.
- Set it to `0.0` only when the point cloud is already clean and your computer can handle the full size.

Good rule:

```text
Higher value = faster and smoother, less detail
Lower value  = slower and more detailed, more memory
```

### Max points for Poisson

Only visible for `Poisson` mode.

This is a safety limit for the number of points used by Poisson reconstruction. If the point cloud is larger than this, the app reduces it before running Poisson.

Default:

```text
5,000,000
```

When to change:

- Lower it if Poisson crashes, freezes, or uses too much RAM.
- Raise it only on a strong computer with enough memory.
- Leave it as default if you are not sure.

### Spacing sample size

Controls how many points are sampled to estimate the average point spacing.

Default:

```text
300,000
```

The spacing estimate is important because the app uses it to calculate normal radius and Ball Pivoting radii.

When to change:

- Increase it for very uneven scans where the automatic spacing estimate seems wrong.
- Decrease it if spacing estimation is slow.
- Usually leave it unchanged.

---

## Point Cloud Densification

Densification adds synthetic points between nearby original points before meshing.

Use it carefully. It can help sparse scans, but it can also create artificial surfaces.

### Densify point cloud

Turns densification on or off.

Default:

```text
Off
```

When to turn on:

- the point cloud is sparse
- Ball Pivoting creates too many gaps
- walls look broken because neighboring points are too far apart

When to keep off:

- the scan is already dense
- you want maximum accuracy from original scan data
- the result starts creating fake surfaces

### Densify factor

Controls how many new points may be added relative to the original point count.

Default:

```text
0.5
```

Example:

```text
0.5 = add up to 50% extra points
1.0 = add up to 100% extra points
```

When to change:

- Increase it if the scan is very sparse.
- Decrease it if the mesh becomes too artificial or too heavy.
- Keep it below `1.0` for normal use.

### Densify K neighbors

Controls how many nearby points are checked when creating new points.

Default:

```text
8
```

When to change:

- Increase it if the point cloud is uneven and new points are not added enough.
- Decrease it if densification connects areas that should stay separate.

### Max edge factor

Limits how far apart points may be before the app refuses to create a new point between them.

Default:

```text
2.5
```

The value is multiplied by the average point spacing.

When to change:

- Increase it if the scan is sparse and gaps are not being filled.
- Decrease it if the app creates false bridges across openings or between opposite walls.

### Max new points

Hard limit for how many synthetic points may be created.

Default:

```text
500,000
```

When to change:

- Lower it if processing is too slow or memory usage is too high.
- Increase it only for large sparse scans on a strong computer.

---

## Normals

Normals describe the direction of the surface. Both Ball Pivoting and Poisson need good normals.

### Normal radius factor

Controls the radius used to estimate point normals.

Default:

```text
3.5
```

The value is multiplied by the average point spacing.

When to change:

- Increase it if normals are noisy and the reconstructed surface looks rough or chaotic.
- Decrease it if fine details are getting smoothed away.

Good rule:

```text
Higher value = smoother normals, less detail
Lower value  = sharper detail, more noise risk
```

### Normal max neighbors

Maximum number of neighboring points used for each normal calculation.

Default:

```text
120
```

When to change:

- Increase it for smoother normals on noisy scans.
- Decrease it for faster processing or sharper local detail.
- If processing becomes very slow, lower this value.

### Orient normals

Makes normals point in a consistent direction.

Default:

```text
On
```

Keep this enabled for most scans. Poisson especially needs consistently oriented normals.

Turn it off only if normal orientation fails or takes too long, and preferably use Ball Pivoting in that case.

### Orient normals K

Controls how many neighbors are used when making normals consistent.

Default:

```text
50
```

When to change:

- Increase it if normals are inconsistent and the mesh has strange inside-out areas.
- Decrease it if orientation is too slow or fails on a large scan.

---

## Poisson Reconstruction

These settings are visible when `Mode` is set to `Poisson`.

### Depth

Controls Poisson reconstruction resolution.

Default:

```text
10
```

When to change:

- Increase it for more detail.
- Decrease it if the process is too slow, uses too much memory, or crashes.
- For very large point clouds, lower values are safer.

Good rule:

```text
Higher depth = more detail, much slower, more RAM
Lower depth  = smoother, faster, less RAM
```

### Scale

Controls how much space Poisson adds around the point cloud during reconstruction.

Default:

```text
1.6
```

When to change:

- Increase it if edges are being cut off.
- Decrease it if Poisson creates too much extra surface around the scan.

### Linear fit

Changes how Poisson fits the surface.

Default:

```text
Off
```

When to change:

- Leave it off for most cave scans.
- Try turning it on if Poisson produces overly rounded surfaces and you want a slightly sharper fit.

### Density trim quantile

Removes low-density Poisson vertices after reconstruction.

Default:

```text
0.01
```

This helps remove weak outer shells and low-confidence areas.

When to change:

- Increase it if Poisson creates many floating or thin outer surfaces.
- Decrease it if important parts of the cave are removed.
- Set to `0.0` to skip density trimming.

### Poisson threads

Controls how many CPU threads Poisson may use.

Default:

```text
0
```

`0` means automatic.

When to change:

- Leave at `0` for normal use.
- Set a fixed number if you want to keep the computer responsive during processing.

### Auto-limit depth

Automatically lowers Poisson depth for large point clouds.

Default:

```text
Off
```

When to turn on:

- Poisson crashes or freezes on large scans
- your computer runs out of memory
- you prefer a safer automatic setting

When to keep off:

- you want full manual control
- you know your computer can handle the selected depth

---

## Output

### Smoothing iterations

Applies light Taubin smoothing to the converted mesh.

Default:

```text
0
```

When to change:

- Increase it if the result is noisy or jagged.
- Keep it at `0` if you want maximum scan detail.
- Use small values first, for example `1` or `2`.

### Color transfer chunk size

Controls how many vertices are processed at once when transferring point colors to the mesh.

Default:

```text
1,000,000
```

When to change:

- Lower it if color transfer uses too much memory.
- Increase it only if you have enough RAM and want fewer processing chunks.
- It usually does not change visual quality, only memory/performance.

---

# Fill Holes / Clean Mesh

Use this step after creating a project with a mesh, or after converting a point cloud to `converted.ply`.

Click:

```text
Fill Holes
```

This step creates:

```text
repaired_mesh.ply
mesh.ply
```

If `Create mobile version` is enabled, it also creates:

```text
mesh_mobile.ply
```

For mesh projects, `Fill Holes` uses:

```text
original.ply
```

For point cloud projects, it uses:

```text
converted.ply
```

---

## Fill Mode

### No filling / cleanup only

Runs cleanup and topology repair, but does not intentionally fill holes.

Use it when:

- the mesh is already good
- you only want cleanup
- hole filling closes entrances or important openings
- you want to generate `mesh.ply` and `mesh_mobile.ply` without changing the shape too much

### Normal hole filling only

Closes detected boundary loops by adding a center point and triangles around the hole.

Use it when:

- the mesh is mostly good
- only small or medium holes need closing
- cave entrances / open tops should stay open
- you want a controlled repair without full surface reconstruction

This is usually the best first choice for normal mesh input.

### Poisson reconstruction only

Runs Screened Poisson reconstruction on the mesh input.

Use it when:

- the mesh is heavily damaged
- there are many holes
- the topology is messy
- normal hole filling is not enough

Be careful: Poisson can change the shape, smooth details, and create a more closed surface than the original scan.

### Poisson + normal hole filling

First runs Poisson reconstruction, then runs normal selective hole filling.

Use it when:

- Poisson improves the mesh but still leaves small holes
- the mesh is very incomplete
- you need a more closed final model

This is the strongest repair mode and also the most likely to change the original shape.

---

## Normal Hole Filling

These settings are active for:

```text
Normal hole filling only
Poisson + normal hole filling
```

### Ignore top percent

Prevents the app from closing holes in the top part of the model.

Default:

```text
10
```

Example:

```text
10 = ignore holes in the highest 10% of the model
0  = do not ignore the top; holes may be closed everywhere
```

Why this exists:

Cave scans often have entrances, shafts, missing ceiling areas, or open upper borders. These should often stay open instead of being capped.

When to change:

- Increase it if the app closes the entrance, shaft, or open top.
- Decrease it if real holes near the top are not being filled.
- Set it to `0` only if the top should also be closed.

### Max hole boundary vertices

Limits how large a hole may be before the app skips it.

Default:

```text
200
```

`0` means no size limit.

What it does:

- small hole loops are filled
- very large openings are skipped
- this prevents the app from closing cave entrances or huge missing scan areas

When to change:

- Increase it if real holes are skipped because they are too large.
- Decrease it if the app closes big openings that should remain open.
- Use `0` only if you really want all detected holes to be fillable.

Good rule:

```text
Lower value = safer, fewer accidental caps
Higher value = fills larger holes, more risk
```

---

## Poisson Reconstruction

These settings are active for:

```text
Poisson reconstruction only
Poisson + normal hole filling
```

### Depth

Controls the reconstruction resolution.

Default:

```text
10
```

When to change:

- Increase it for more detail.
- Decrease it if the process is slow, memory-heavy, or unstable.
- Use lower values for very large scans.

Good rule:

```text
Higher depth = sharper and heavier
Lower depth  = smoother and safer
```

### Full depth

Controls how many octree levels are fully expanded during Poisson reconstruction.

Default:

```text
5
```

When to change:

- Usually leave it unchanged.
- Increase only if you understand the Poisson settings and need more uniform reconstruction detail.
- Decrease if reconstruction is too heavy.

### CG depth

Controls the conjugate-gradient solver depth used by the Poisson reconstruction.

Default:

```text
0
```

For normal use, keep it at `0`.

Change it only for advanced testing when Poisson quality or performance needs tuning.

### Scale

Controls the reconstruction volume around the mesh.

Default:

```text
1.02
```

When to change:

- Increase it if the reconstruction cuts off edges.
- Decrease it if Poisson creates too much extra outside surface.
- Keep close to `1.0` for tight reconstruction around the original mesh.

### Samples per node

Controls how many samples are expected per reconstruction node.

Default:

```text
1.5
```

When to change:

- Increase it for noisy scans to make the result smoother and more stable.
- Decrease it to preserve more fine detail, but expect more noise.

### Point weight

Controls how strongly the reconstruction follows the original mesh points.

Default:

```text
8.0
```

When to change:

- Increase it if Poisson changes the shape too much and should follow the scan more closely.
- Decrease it if the result is noisy and needs more smoothing.

### Iterations

Controls solver iterations.

Default:

```text
8
```

When to change:

- Increase it if the Poisson result looks unfinished or unstable.
- Decrease it if processing is too slow.
- Usually leave it unchanged.

### Preclean

Runs Poisson precleaning before reconstruction.

Default:

```text
On
```

Keep it enabled for most scans.

Turn it off only if precleaning removes important geometry or if you are testing a problematic mesh.

---

## Output / Cleanup

### Keep only largest component

Keeps the largest connected mesh component and removes smaller disconnected pieces.

Default:

```text
On
```

Keep it enabled for most Erdstall scans because it removes small floating fragments.

Turn it off if the model intentionally contains several separate parts that must stay.

### Smooth mesh

Applies smoothing after filling/reconstruction.

Default:

```text
Off
```

When to turn on:

- the mesh looks jagged
- Poisson or hole filling creates rough areas
- visual smoothness is more important than exact scan roughness

When to keep off:

- you want maximum original detail
- wall texture/geometry should stay sharp

### Smoothing iterations

Controls how much smoothing is applied.

Default:

```text
3
```

Only active when `Smooth mesh` is enabled.

When to change:

- Use `1–3` for light smoothing.
- Use higher values only if the mesh is very rough.
- Lower it if details become too soft.

### Mesh reduction percent

Controls how strongly the mobile mesh is reduced.

Default:

```text
15
```

This means the mobile mesh keeps about `85%` of the original faces and removes about `15%`.

When to change:

- Increase it for a smaller mobile file.
- Decrease it if the mobile mesh loses too much detail.
- Use stronger reduction only after checking the result visually.

Examples:

```text
10 = light reduction
15 = default reduction
30 = stronger reduction
50 = much smaller, but visible detail loss likely
```

### Transfer texture to vertex colors

Transfers texture/color information to vertex colors in the repaired mesh.

Default:

```text
On
```

Keep it enabled if the scan has useful color or texture data.

Turn it off if:

- you only need geometry
- the texture/color transfer causes problems
- the original colors are wrong or not needed

### Create mobile version

Creates a reduced mesh for mobile/web use.

Default:

```text
On
```

Output:

```text
mesh_mobile.ply
```

Keep it enabled if the model will be used in the web tour.

Turn it off only if you need the full-quality mesh and do not need a mobile version.

---

# Path points and path calculation

## Add path points

Path points are imported from a MeshLab `.pp` picked-points file.

Click:

```text
Add Path Points
```

The `.pp` file must contain at least 6 picked points:

```text
first 3 points  = start area
next 3 points   = end area
```

The app averages these points and creates:

```text
path_points.csv
```

## Calculate path

Before this step, Fiji must be configured and validated in `Setup`.

Click:

```text
Calculate Path
```

Required files:

```text
mesh.ply
path_points.csv
```

Outputs:

```text
path.csv
path.json
```

---

# Export GLB

Click the toolbar action:

```text
Convert GLB
```

This exports:

```text
mesh.glb
mesh_mobile.glb
```

The export window can also add a human scale model, rotate the model, create a mobile GLB, and optimize the GLB.

---

# Create XML metadata

Select a project and click:

```text
Create XML metadata
```

Fill the form and confirm.

Output:

```text
metadata.xml
```

---

# Edit textures

Open:

```text
Texture Changes
```

Choose an input texture folder and adjust:

- brightness
- contrast
- saturation
- sharpness

You can overwrite the same folder or choose a different output folder.

---

# Troubleshooting

## `Calculate Path` is disabled

Check that both files exist:

```text
mesh.ply
path_points.csv
```

Also validate Fiji in:

```text
Setup → Validate setup
```

## `Fill Holes` is disabled

For point cloud projects, first run:

```text
Convert Point Cloud to Mesh
```

For normal mesh projects, make sure `original.ply` exists.

## `Convert GLB` says `mesh.ply` is missing

Run `Fill Holes` first. GLB export uses:

```text
mesh.ply
```

## Fiji works manually but validation fails on macOS

Check the resolved executable:

```text
/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx
```

Then run:

```bash
chmod +x "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx"
```

After that, go back to the app and run:

```text
Setup → Validate setup
```

## Point cloud conversion is too slow

Try these changes:

```text
Increase Downsample voxel size
Lower Max points for Poisson
Lower Poisson depth
Lower Normal max neighbors
Turn off Densify point cloud
```

## Ball Pivoting creates too many holes

Try these changes:

```text
Slightly increase Ball radius factors
Turn on Densify point cloud
Increase Densify factor carefully
Use Fill Holes after conversion
```

## Ball Pivoting creates false surfaces

Try these changes:

```text
Lower Ball radius factors
Lower Max edge factor
Turn off Densify point cloud
Use smaller Max hole size if small-hole filling is enabled
```

## Poisson changes the shape too much

Try these changes:

```text
Use Ball Pivoting instead
Lower Poisson scale
Increase Point weight
Lower Depth if the output is too heavy
Increase Density trim quantile if extra outer shells appear
```

## Fill Holes closes entrances or open shafts

Try these changes:

```text
Increase Ignore top percent
Lower Max hole boundary vertices
Use No filling / cleanup only
Avoid Poisson + normal hole filling for that model
```

## Large files are slow

Large `.ply` scans can take a long time. Point cloud conversion, Poisson reconstruction, path calculation, and GLB optimization are the heaviest steps.
