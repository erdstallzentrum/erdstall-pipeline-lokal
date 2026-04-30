from pathlib import Path
from typing import Iterable
from PIL import Image, ImageEnhance
import cv2
import numpy as np

from .config import IMAGE_DEFAULT_FACTOR
from .settings.texture_settings import TextureJob, TextureSettings


def _adjust_texture(
    image_path: str | Path,
    output_image_path: str | Path,
    settings: TextureSettings,
):
    img = Image.open(image_path).convert("RGB")

    img = _adjust_image_object(img, settings)
    img = _adjust_sharpness_with_opencv(img, settings.sharpness)
    img.save(output_image_path)


def _adjust_image_object(
    img: Image.Image,
    settings: TextureSettings
) -> Image.Image:
    if settings.brightness != IMAGE_DEFAULT_FACTOR:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(settings.brightness)

    if settings.contrast != IMAGE_DEFAULT_FACTOR:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(settings.contrast)

    if settings.saturation != IMAGE_DEFAULT_FACTOR:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(settings.saturation)

    return img


def _adjust_sharpness_with_opencv(
    img: Image.Image,
    sharpness=IMAGE_DEFAULT_FACTOR,
) -> Image.Image:
    if sharpness == IMAGE_DEFAULT_FACTOR:
        return img

    img_np = np.array(img)

    if sharpness > 1.0:
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ], dtype=np.float32)

        filtered = cv2.filter2D(img_np, -1, kernel)
        blend_amount = min(sharpness - 1.0, 1.0)
        result = cv2.addWeighted(img_np, 1.0 - blend_amount, filtered, blend_amount, 0)

    else:
        blur_intensity = 1.0 - sharpness
        blur_size = int(blur_intensity * 30) * 2 + 1
        blur_size = max(3, blur_size)

        result = cv2.blur(img_np, (blur_size, blur_size))

    return Image.fromarray(result)


def process_model_textures(
    input_folder: str | Path,
    output_folder: str | Path,
    settings: TextureSettings,
    supported_formats: Iterable[str] = (".jpg",".jpeg", ".png"),
) -> None:
    
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    supported_formats = tuple(supported_formats)

    output_folder.mkdir(parents=True, exist_ok=True)

    for input_path in input_folder.iterdir():
        if input_path.is_file() and input_path.name.lower().endswith(supported_formats):
            output_path = output_folder / input_path.name
            _adjust_texture(
                input_path,
                output_path,
                settings,
            )

                
def process_model_textures_job(job: TextureJob) -> None:
    process_model_textures(
        input_folder = job.input_folder,
        output_folder = job.output_folder,
        settings = job.settings,
    )