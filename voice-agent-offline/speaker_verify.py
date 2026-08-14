import torch
import soundfile as sf
from speechbrain.inference.speaker import SpeakerRecognition

verification_model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec-ecapa-voxceleb"
)

def verify_speaker(clip_path, reference_path="enrolled_voice.wav", threshold=0.10):
    # Load audio manually to bypass speechbrain's Windows k2 lazy-import bug
    sig1, _ = sf.read(reference_path)
    sig2, _ = sf.read(clip_path)
    
    t1 = torch.tensor(sig1).unsqueeze(0).float()
    t2 = torch.tensor(sig2).unsqueeze(0).float()
    
    score, _ = verification_model.verify_batch(t1, t2)
    score_val = float(score[0])
    
    # Use a custom, more forgiving threshold (default is ~0.25, which is too strict for quiet laptop mics)
    return (score_val > threshold), score_val
