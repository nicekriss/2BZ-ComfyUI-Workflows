import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import numpy as np
import torch

import folder_paths
import comfy.model_management as mm


SETUP = Path(__file__).with_name("setup.json")
STYLES = {
    "Piano Pop / 피아노 발라드": "piano pop ballad, warm expressive female lead vocal, acoustic piano, rounded bass, brushed drums, gentle strings, intimate hopeful mood, memorable melody, 88 BPM",
    "Indie Rock / 인디 록": "energetic indie rock, gritty melodic male lead vocal, crunchy electric guitars, driving live drums, punchy bass, anthemic uplifting chorus, 132 BPM",
    "Vocal Jazz / 보컬 재즈": "intimate vocal jazz, warm soft female alto, acoustic jazz piano, upright bass, brushed drums, mellow tenor saxophone fills, laid-back swing, extended chords, cozy late-night club, 104 BPM",
    "Dance Pop / 댄스 팝": "euphoric electronic dance pop, bright confident female lead vocal, four-on-the-floor house kick, crisp claps, pulsating synth bass, shimmering arpeggios, uplifting catchy chorus, 124 BPM",
}
DEFAULT_LYRICS = "[Verse]\n창가에 내려앉은 아침빛\n식어 간 커피 위로 번지네\n멈췄던 시계가 다시 돌아\n오늘은 한 걸음을 내딛어\n\n[Chorus]\n조금 느려도 괜찮아\n나의 속도로 걸어가\n작은 빛 하나 품에 안고\n다시 나의 하루를 열어\n\n[Outro]\n다시 나의 하루를 열어"


class YuE2LocalModel:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"model": (["YuE2-3B + YuE2-VAE"],), "memory_gib": ("INT", {"default": 24, "min": 8, "max": 96})}}

    RETURN_TYPES = ("YUE2_MODEL",)
    FUNCTION = "configure"
    CATEGORY = "YuE2"

    def configure(self, model, memory_gib):
        if model != "YuE2-3B + YuE2-VAE":
            raise ValueError("Unknown YuE2 model")
        if not SETUP.is_file():
            raise FileNotFoundError("Run Install-YuE2.bat from the 2BZ YuE2 installer first.")
        config = json.loads(SETUP.read_text(encoding="utf-8"))
        for path in (Path(config["runtime"]), Path(config["model"]) / "model.safetensors", Path(config["vae"]) / "model.safetensors"):
            if not path.is_file():
                raise FileNotFoundError(str(path))
        return ({**config, "memory_gib": memory_gib},)


class YuE2Song:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "genre": (list(STYLES),),
            "lyrics": ("STRING", {"multiline": True, "default": DEFAULT_LYRICS}),
            "style_override": ("STRING", {"multiline": True, "default": "", "tooltip": "비워두면 선택한 장르를 사용합니다. 입력하면 장르 스타일을 대체합니다."}),
        }}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("style", "lyrics")
    FUNCTION = "compose"
    CATEGORY = "YuE2"

    def compose(self, genre, lyrics, style_override):
        style = style_override.strip() or (STYLES[genre] + ", short complete song about one minute, brief intro, resolved ending")
        return style, lyrics


class YuE2LocalGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("YUE2_MODEL",),
            "style": ("STRING", {"forceInput": True}),
            "lyrics": ("STRING", {"forceInput": True}),
            "seed": ("INT", {"default": 831001, "min": 0, "max": 2**63 - 1, "control_after_generate": True}),
            "planning": (["full", "melody", "off"], {"default": "full"}),
        }}

    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "generate"
    CATEGORY = "YuE2"

    def generate(self, model, style, lyrics, seed, planning, abc=""):
        if abc.strip() and planning == "off":
            raise ValueError("ABC 악보를 사용할 때 planning을 full 또는 melody로 선택하세요.")
        mm.unload_all_models()
        mm.soft_empty_cache()
        output = Path(folder_paths.get_output_directory()).resolve() / "YuE2" / f"{time.strftime('%Y%m%d_%H%M%S')}_{seed}_{uuid.uuid4().hex[:6]}"
        output.mkdir(parents=True)
        request = {"model": model, "song": {"style": style, "lyrics": lyrics, "seed": seed, "cot": planning}, "output": str(output)}
        if abc.strip():
            request["song"]["abc"] = abc.strip()
        request_path = output / "job.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONNOUSERSITE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
        log_path = output / "generation.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([model["runtime"], "-u", str(Path(__file__).with_name("worker.py")), str(request_path)], stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                while process.poll() is None:
                    mm.throw_exception_if_processing_interrupted()
                    time.sleep(0.5)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
        if process.returncode:
            raise RuntimeError(f"YuE2 failed. Log: {log_path}\n{log_path.read_text(encoding='utf-8')[-4000:]}")
        audio = np.load(output / "audio.npy", allow_pickle=False)
        sample_rate = json.loads((output / "result.json").read_text(encoding="utf-8"))["sample_rate"]
        return ({"waveform": torch.from_numpy(audio.T.copy()).unsqueeze(0), "sample_rate": sample_rate},)


NODE_CLASS_MAPPINGS = {"YuE2LocalModel": YuE2LocalModel, "YuE2Song": YuE2Song, "YuE2LocalGenerate": YuE2LocalGenerate}
NODE_DISPLAY_NAME_MAPPINGS = {"YuE2LocalModel": "YuE2 · Model", "YuE2Song": "YuE2 · Genre & Lyrics", "YuE2LocalGenerate": "YuE2 · Generate Song"}
