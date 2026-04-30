import json
from pathlib import Path
from collections.abc import Callable
import pymeshlab


LogCallback = Callable[[str], None] | None

def find_patches(
    filled_holes_input_file: str | Path,
    original_input_file: str | Path ,
    output_files_path: str | Path ,
    log_callback: LogCallback = None
) -> None:

    filled_holes_input_file = Path(filled_holes_input_file)
    original_input_file = Path(original_input_file)
    out_dir = Path(output_files_path)

    def log(message: str)-> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    log("Finding patches...")
    ms = pymeshlab.MeshSet()
    log("Loading original mesh...")
    ms.load_new_mesh(str(original_input_file))
    log("Loading repaierd mesh...")
    ms.load_new_mesh(str(filled_holes_input_file))
    log("Computing Hausdorff distance...")
    ms.get_hausdorff_distance(
        sampledmesh=1,
        targetmesh=0,
        savesample=True,
        maxdist=pymeshlab.PercentageValue(0.1),
    )
    log("Selecting patch candidates...")
    ms.compute_selection_by_scalar_per_vertex(minq=0.1)
    ms.apply_selection_inverse()
    ms.meshing_remove_selected_vertices_and_faces()
    log("Removing small connected components...")
    ms.meshing_remove_connected_component_by_diameter(
        mincomponentdiag=pymeshlab.PercentageValue(2.5)
    )
    log("Splitting connected components...")
    ms.generate_splitting_by_connected_components(delete_source_mesh=True)

    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Saving patch meshes to: {out_dir}")

    patches = []
    for i in range(len(ms)):
        if i < len(ms) - 3:
            ms.set_current_mesh(i + 4)
        output_file = out_dir / f'patch_{i}.ply'
        bbox = ms.current_mesh().bounding_box()
        min_coords = bbox.min()
        max_coords = bbox.max()
        center = (min_coords + max_coords) / 2
        ms.save_current_mesh(str(output_file))

        patches.append(
            {
                'id': i,
                'path': output_file.name,
                'center': {
                    'x': float(center[0]),
                    'y': float(center[1]),
                    'z': float(center[2]),
                },
            }
        )

    result = {'total_patches': len(patches), 'patches': patches}
    json_path = out_dir.parent / 'patches.json'
    with json_path.open( 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    log("Finding patches done.")


def get_patches_json(mesh_dir: str):
    path = Path(mesh_dir) / "patches.json"
    if not path.exists():
        return None
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def get_patches_paths(mesh_dir: str | Path):
    data = get_patches_json(str(mesh_dir))
    if data is None:
        return None
    return [patch["path"] for patch in data["patches"]]
