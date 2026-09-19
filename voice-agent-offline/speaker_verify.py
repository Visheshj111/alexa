import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
import torch
import soundfile as sf
import numpy as np
from speechbrain.inference.speaker import SpeakerRecognition

verification_model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec-ecapa-voxceleb"
)

# Preload enrolled voice embedding tensor in RAM once
_ref_tensor = None
_default_ref_path = "enrolled_voice.wav"
if os.path.exists(_default_ref_path):
    sig_ref, _ = sf.read(_default_ref_path)
    _ref_tensor = torch.tensor(sig_ref).unsqueeze(0).float()

def verify_speaker(clip_source, reference_path="enrolled_voice.wav", threshold=0.10):
    global _ref_tensor
    if _ref_tensor is None and os.path.exists(reference_path):
        sig1, _ = sf.read(reference_path)
        _ref_tensor = torch.tensor(sig1).unsqueeze(0).float()
        
    if _ref_tensor is None:
        # If no enrollment exists, treat as verified
        return True, 1.0

    if isinstance(clip_source, np.ndarray):
        sig2 = clip_source.flatten().astype(np.float32)
        if clip_source.dtype == np.int16:
            sig2 = sig2 / 32768.0
    else:
        sig2, _ = sf.read(clip_source)
        sig2 = sig2.flatten().astype(np.float32)
        
    t2 = torch.tensor(sig2).unsqueeze(0).float()
    score, _ = verification_model.verify_batch(_ref_tensor, t2)
    score_val = float(score[0])
    
    return (score_val > threshold), score_val
