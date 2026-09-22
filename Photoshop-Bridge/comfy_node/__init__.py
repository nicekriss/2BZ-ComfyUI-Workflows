"""TooBusy Photoshop Bridge. Install this directory as a ComfyUI custom node."""
import base64
import hashlib
import hmac
import io
import ipaddress
import json
import uuid
from pathlib import Path

import numpy as np
import torch
from aiohttp import web
from PIL import Image
import folder_paths
from nodes import SaveImage
from server import PromptServer

from .pixels import MAX_BYTES, contained, decode_file, decode_raw, result_pixels

TOKEN = json.loads((Path(__file__).parent / "pairing.json").read_text("utf-8"))["token"]
PREFIX = "TooBusyPS"


def input_path(name):
    if not name.startswith(PREFIX + "/"):
        raise ValueError("Use an image synced by TooBusy Photoshop Bridge")
    return contained(Path(folder_paths.get_input_directory()) / PREFIX, name[len(PREFIX) + 1:])


class TooBusyPhotoshopInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("STRING", {"default": ""}),
                             "selection": ("STRING", {"default": ""})},
                "optional": {"matte_white": ("BOOLEAN", {"default": False})}}

    RETURN_TYPES = ("IMAGE", "MASK", "MASK")
    RETURN_NAMES = ("image", "selection", "alpha")
    FUNCTION = "load"
    CATEGORY = "TooBusy/Photoshop"

    def load(self, image, selection="", matte_white=False):
        with Image.open(input_path(image)) as source:
            rgba = np.array(source.convert("RGBA"), dtype=np.float32) / 255.0
        rgb = torch.from_numpy(rgba[:, :, :3].copy())[None, ...]
        alpha = torch.from_numpy(rgba[:, :, 3].copy())[None, ...]
        if matte_white:
            rgb = rgb * alpha.unsqueeze(-1) + (1 - alpha.unsqueeze(-1))
        mask = torch.zeros_like(alpha)
        if selection:
            with Image.open(input_path(selection)) as source:
                if source.size != (rgba.shape[1], rgba.shape[0]):
                    raise ValueError("Selection and input dimensions differ; sync again")
                mask = torch.from_numpy(np.array(source.convert("L"), dtype=np.float32) / 255.0)[None, ...]
        return rgb, mask, alpha

    @classmethod
    def IS_CHANGED(cls, image, selection="", matte_white=False):
        digest = hashlib.sha256()
        digest.update(bytes([bool(matte_white)]))
        for name in (image, selection):
            if name:
                digest.update(input_path(name).read_bytes())
        return digest.hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, image, selection="", matte_white=False):
        try:
            for name in (image, selection):
                if name and not input_path(name).is_file():
                    return "Synced input is missing; sync again"
            return True if image else "Sync an image first"
        except ValueError as error:
            return str(error)


class TooBusyPhotoshopOutput(SaveImage):
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",)}, "optional": {"alpha": ("MASK",)},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}

    FUNCTION = "save_bridge"
    CATEGORY = "TooBusy/Photoshop"

    def save_bridge(self, images, alpha=None, prompt=None, extra_pnginfo=None):
        if alpha is not None:
            if images.shape[:3] != alpha.shape:
                raise ValueError("Output alpha must match the image batch and dimensions")
            images = torch.cat((images[:, :, :, :3], alpha.unsqueeze(-1)), dim=-1)
        return self.save_images(images, filename_prefix=PREFIX + "/result",
                                prompt=prompt, extra_pnginfo=extra_pnginfo)


def authorize(request):
    try:
        local = ipaddress.ip_address(request.remote).is_loopback
    except (ValueError, TypeError):
        local = False
    if not local or not hmac.compare_digest(request.headers.get("X-TooBusy-Token", ""), TOKEN):
        raise web.HTTPForbidden(text="Local paired Photoshop plugin required")


routes = PromptServer.instance.routes


@routes.get("/toobusy/ps/v1/info")
async def info(request):
    authorize(request)
    return web.json_response({"protocol": 1, "version": "0.1.0", "max_pixels": MAX_BYTES // 4})


@routes.post("/toobusy/ps/v1/input")
async def upload(request):
    authorize(request)
    # Per-request ceiling also applies when Content-Length is absent.
    data = bytearray()
    async for chunk in request.content.iter_chunked(1024 * 1024):
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise web.HTTPRequestEntityTooLarge(max_size=MAX_BYTES, actual_size=len(data))
    try:
        q = request.query
        if q.get("format") == "raw":
            image = decode_raw(bytes(data), q["width"], q["height"], q["components"])
        else:
            image = decode_file(bytes(data))
        directory = Path(folder_paths.get_input_directory()) / PREFIX
        directory.mkdir(parents=True, exist_ok=True)
        name = uuid.uuid4().hex + ".png"
        image.save(directory / name)
        return web.json_response({"name": PREFIX + "/" + name, "width": image.width, "height": image.height})
    except (ValueError, KeyError, OSError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error


@routes.get("/toobusy/ps/v1/result")
async def result(request):
    authorize(request)
    try:
        q = request.query
        # Relative name includes any subfolder below the dedicated output root.
        path = contained(Path(folder_paths.get_output_directory()) / PREFIX, q["name"])
        image = result_pixels(path, q.get("width"), q.get("height"))
        if q.get("preview") == "1":
            image.thumbnail((512, 512))
            background = Image.new("RGB", image.size, (48, 48, 48))
            background.paste(image, mask=image.getchannel("A"))
            encoded = io.BytesIO()
            background.save(encoded, format="JPEG", quality=85)
            return web.json_response({"data": "data:image/jpeg;base64," + base64.b64encode(encoded.getvalue()).decode("ascii")})
        return web.Response(body=image.tobytes(), content_type="application/octet-stream",
                            headers={"X-Width": str(image.width), "X-Height": str(image.height), "X-Components": "4"})
    except FileNotFoundError as error:
        raise web.HTTPNotFound(text="Result file is missing") from error
    except (ValueError, KeyError, OSError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error


NODE_CLASS_MAPPINGS = {"TooBusyPhotoshopInput": TooBusyPhotoshopInput,
                       "TooBusyPhotoshopOutput": TooBusyPhotoshopOutput}
NODE_DISPLAY_NAME_MAPPINGS = {"TooBusyPhotoshopInput": "TooBusy Photoshop Input",
                              "TooBusyPhotoshopOutput": "TooBusy Photoshop Result"}
