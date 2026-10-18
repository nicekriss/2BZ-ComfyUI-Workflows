import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


PACKAGE = Path(__file__).parent / "YuE2/custom_nodes/ComfyUI-YuE2"


def load(name):
    spec = importlib.util.spec_from_file_location("test_yue2_" + name, PACKAGE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerationTests(unittest.TestCase):
    def test_token_limit_reaches_worker_and_old_calls_keep_default(self):
        modules = {name: MagicMock() for name in (
            "numpy", "torch", "folder_paths", "comfy", "comfy.model_management",
            "comfy.utils", "comfy_execution", "comfy_execution.utils", "server")}
        with patch.dict(sys.modules, modules), tempfile.TemporaryDirectory() as temp:
            nodes = load("nodes")
            nodes.folder_paths.get_output_directory.return_value = temp
            nodes.get_executing_context.return_value = None
            process = SimpleNamespace(poll=lambda: 0, returncode=0)

            def finish(command, **kwargs):
                job = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
                (Path(job["output"]) / "result.json").write_text('{"sample_rate":48000}')
                return process

            with patch.object(nodes.subprocess, "Popen", side_effect=finish), patch.object(nodes.subprocess, "CREATE_NO_WINDOW", 0, create=True):
                node = nodes.YuE2LocalGenerate()
                for limit in (None, 5000, 100):
                    with self.subTest(limit=limit):
                        options = {} if limit is None else {"max_tokens": limit}
                        node.generate({"runtime": "python"}, "piano", "lyrics", 1, "melody", "X:1\nK:C\nCDEF|", **options)
                        command = nodes.subprocess.Popen.call_args.args[0]
                        job = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
                        self.assertEqual(job["max_tokens"], 9000 if limit is None else limit)
                        self.assertEqual(job["song"]["abc"], "X:1\nK:C\nCDEF|")
                self.assertEqual(node.INPUT_TYPES()["optional"]["max_tokens"][1]["default"], 9000)

    def test_worker_overrides_only_semantic_limit(self):
        pipeline = MagicMock()
        pipeline.generation_config.semantic.min_tokens = 200
        pipeline.return_value.sample_rate = 48000
        pipeline.return_value.truncated = True
        pipeline.return_value.timing = {}
        factory = MagicMock(return_value=pipeline)
        torch = MagicMock()
        torch.cuda.max_memory_allocated.return_value = 0
        modules = {"numpy": MagicMock(), "torch": torch, "yue2": SimpleNamespace(YuE2Pipeline=SimpleNamespace(from_pretrained=factory))}
        with patch.dict(sys.modules, modules), tempfile.TemporaryDirectory() as temp:
            worker = load("worker")
            path = Path(temp) / "job.json"
            for limit in (None, 5000, 100):
                with self.subTest(limit=limit):
                    job = {"model": {"model": "weights", "vae": "vae", "memory_gib": 12},
                           "song": {"style": "piano", "lyrics": "lyrics", "cot": "off", "seed": 1}, "output": temp}
                    if limit is not None:
                        job["max_tokens"] = limit
                    path.write_text(json.dumps(job))
                    with patch.object(worker.sys, "argv", ["worker.py", str(path)]):
                        worker.main()
                    expected = 9000 if limit is None else limit
                    self.assertEqual(pipeline.call_args.kwargs, {**job["song"], "semantic_sampling": {"max_tokens": expected, "min_tokens": min(200, expected)}})
                    self.assertTrue(json.loads((Path(temp) / "metrics.json").read_text())["truncated"])


if __name__ == "__main__":
    unittest.main()
