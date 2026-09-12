"""Exercise the actual host-side audio imports and pitch detector without models."""
from importlib.metadata import version
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa
import torch
import torchaudio


def main():
    if not librosa.__version__.startswith('0.11.') or not sf.__version__.startswith('0.13.'):
        raise RuntimeError('ABC Studio requires librosa 0.11.x and soundfile 0.13.x.')
    signal = .2 * np.sin(2 * np.pi * 440 * np.arange(8000) / 16000)
    with tempfile.TemporaryDirectory(prefix='abc-audio-check-') as temp:
        path = Path(temp) / 'tone.wav'
        sf.write(path, signal, 16000, subtype='PCM_16')
        audio, rate = sf.read(path)
        pitch, voiced, _ = librosa.pyin(audio, sr=rate, fmin=200, fmax=800, frame_length=1024)
        if not voiced.any() or abs(float(np.nanmedian(pitch)) - 440) > 5:
            raise RuntimeError('ABC audio pitch smoke test failed.')
    if not callable(torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS.get_model):
        raise RuntimeError('ComfyUI torchaudio lacks the vocal separation model.')
    print('ABC AUDIO VERIFIED: WAV roundtrip and 440 Hz pitch; existing Torch', torch.__version__,
          'torchaudio', version('torchaudio'), flush=True)


if __name__ == '__main__':
    main()
