"""Convert the pinned author's BF16 ControlNet to the tested FP16 representation."""
import sys
import torch
from safetensors.torch import load_file, save_file
tensors=load_file(sys.argv[1],device='cpu')
for key,tensor in tensors.items():
    if tensor.is_floating_point():
        if not torch.isfinite(tensor).all() or tensor.abs().max()>65504:raise ValueError('FP16 범위를 벗어나는 가중치: '+key)
        tensors[key]=tensor.to(torch.float16)
save_file(tensors,sys.argv[2])
