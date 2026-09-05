"""Read-only capability check for the MiniMax H3 VSA node CUDA path."""
import inspect
import sys
from pathlib import Path

import torch
import comfy_kitchen
from comfy_kitchen.backends import cuda

sys.path.insert(0, str(Path.cwd()))
from comfy_api.latest import io

assert callable(getattr(comfy_kitchen, 'sol_attn', None)), 'comfy-kitchen sol_attn is missing'
kernel = getattr(cuda, 'sol_attn_chunked', None)
assert callable(kernel), 'comfy-kitchen CUDA sol_attn_chunked is missing'
required = {'tail', 'block_len', 'coarse_gate', 'topk_ratio'}
assert required <= set(inspect.signature(kernel).parameters), 'VSA kernel arguments are missing'
assert torch.cuda.is_available(), 'CUDA is unavailable in this Python environment'
assert torch.cuda.get_device_capability()[0] >= 8, 'This node requires SM 8.0 or newer'
assert torch.cuda.is_bf16_supported(), 'BF16 support is required'
assert hasattr(io, 'DynamicCombo'), 'Update ComfyUI for DynamicCombo support'
t, h, d = 128, 1, 128
qkv = torch.randn(t, 3 * h * d, device='cuda', dtype=torch.bfloat16)
freqs = torch.eye(2, device='cuda').reshape(1, 1, 1, 2, 2).expand(t, 1, d // 2, 2, 2).contiguous()
norm = torch.ones(d, device='cuda', dtype=torch.bfloat16)
lengths = torch.full((2,), 64, device='cuda', dtype=torch.int32)
gate = torch.zeros(1, t, h, d, device='cuda', dtype=torch.bfloat16)
out, _, _ = kernel(lambda: iter([qkv]), t, h, freqs, (norm, norm),
                   topk_ratio=0.1, tail=False, block_len=lengths, coarse_gate=gate)
torch.cuda.synchronize()
assert out.shape == (1, t, h, d) and torch.isfinite(out).all().item(), 'VSA kernel smoke test failed'
print('VSA API/GPU and small CUDA kernel test passed:', torch.cuda.get_device_name())
print('Python:', sys.executable)
print('No full model inference performed; verify VSA tiles and no fallback in the render log.')
