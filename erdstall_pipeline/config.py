from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PLY_DIR = DATA_DIR / "ply"

WORK_DIRNAME = "_path_tmp"
FILES_DIR = DATA_DIR / WORK_DIRNAME

ORIGINAL_MESH = "original.ply"
REPAIRED_MESH = "repaired_mesh.ply"
FINAL_MESH = "mesh.ply"
MESH_MOBILE = "mesh_mobile.ply"
CONVERTED_MESH = "converted.ply"
XML_FILENAME = "metadata.xml"
MESH_GLB = "mesh.glb"
MESH_MOBILE_GLB = "mesh_mobile.glb"

TEXTURE_DIR = "mesh"
BACKUP_TEXTURE_DIR = "textures_backup"

IMAGE_DEFAULT_FACTOR = 1.0
INITIAL_MESH_REDUCTION_FACTOR = 15
MOBILE_COMPRESSION_PERCENT = 25

PATH_POINTS_FILENAME = "path_points.csv"
PATH_OUTPUT_FILENAME = "path.csv"
PATH_JSON_FILENAME = "path.json"

RAW_FROM_PLY_FILENAME = "output_from_ply.raw"
VOLUME_FILENAME = "volume.raw"
SKELETON_FILENAME = "skeleton.raw"
SKELETON_VOLUME_FILENAME = "skeleton_volume.raw"
PATH_MESH_FILENAME = "mesh_path.ply"


XML_NAMESPACE = "http://erdstall-metadaten.org"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
XML_SCHEMA_LOCATION = "http://erdstall-metadaten.org metadaten.xsd"

SIZE = 180