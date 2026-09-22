"""Image wire format shared by the HTTP routes and tests. No Comfy imports."""
import io
from pathlib import Path
from PIL import Image, ImageCms, ImageOps

MAX_PIXELS = 16_777_216
MAX_BYTES = MAX_PIXELS * 4


def dimensions(width, height):
    width, height = int(width), int(height)
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise ValueError("Image must contain 1 to 16,777,216 pixels")
    return width, height


def decode_raw(data, width, height, components):
    width, height = dimensions(width, height)
    components = int(components)
    if components not in (1, 3, 4) or len(data) != width * height * components:
        raise ValueError("Pixel byte count or channel count is invalid")
    return Image.frombytes({1: "L", 3: "RGB", 4: "RGBA"}[components], (width, height), data)


def decode_file(data):
    with Image.open(io.BytesIO(data)) as source:
        dimensions(*source.size)
        if source.format not in ("PNG", "JPEG", "WEBP"):
            raise ValueError("Choose a PNG, JPEG or WebP file")
        source.load()
        source = ImageOps.exif_transpose(source)
        alpha = source.convert("RGBA").getchannel("A")
        profile = source.info.get("icc_profile")
        if profile:
            source = ImageCms.profileToProfile(
                source, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                ImageCms.createProfile("sRGB"), outputMode="RGB")
        else:
            source = source.convert("RGB")
        source.putalpha(alpha)
        return source


def contained(root, name):
    root = Path(root).resolve()
    candidate = (root / name).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("Path is outside the bridge folder")
    return candidate


def result_pixels(path, width=None, height=None):
    with Image.open(path) as source:
        dimensions(*source.size)
        image = source.convert("RGBA")
    if width is not None or height is not None:
        size = dimensions(width, height)
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image
