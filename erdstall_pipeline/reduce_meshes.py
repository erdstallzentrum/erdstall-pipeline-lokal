import pymeshlab

from .config import INITIAL_MESH_REDUCTION_FACTOR, MOBILE_COMPRESSION_PERCENT

def _apply_decimation(ms: pymeshlab.MeshSet, compression_percentage: float, original_faces: int) -> None:
    if original_faces == 0 or ms.current_mesh().face_number() == 0:
        return

    target_perc = 1 - (compression_percentage / 100)
    target_faces = int(original_faces * target_perc)

    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=target_faces,
        preserveboundary=True,
        preservenormal=True,
        preservetopology=True,
        optimalplacement=True,
        planarquadric=False,
        qualityweight=False,
        autoclean=True
    )

    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()


def _save_mesh(ms: pymeshlab.MeshSet, file_path: str) -> None:
    ms.save_current_mesh(
        file_path,
        save_vertex_color=True,
        save_wedge_texcoord=False,
        save_textures=False
    )


def reduce_file_size(file_path: str, initial_mesh_reduction: bool = True) -> str | None:
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(file_path)
    original_faces = ms.current_mesh().face_number()

    if initial_mesh_reduction:
        ms_version = pymeshlab.MeshSet()
        ms_version.load_new_mesh(file_path)
        _apply_decimation(ms_version, INITIAL_MESH_REDUCTION_FACTOR, original_faces)
        _save_mesh(ms_version, file_path)

        return file_path

    ms_version = pymeshlab.MeshSet()
    ms_version.load_new_mesh(file_path)
    _apply_decimation(ms_version, MOBILE_COMPRESSION_PERCENT, original_faces)

    file_ending = file_path.split('.')[-1]
    file_name = file_path.rsplit('.', 1)[0]
    output_path = f"{file_name}_mobile.{file_ending}"
    
    _save_mesh(ms_version, output_path)
    return output_path