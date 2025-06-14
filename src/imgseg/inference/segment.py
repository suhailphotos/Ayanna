from pathlib import Path
from PIL import Image
import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

# ---------------------------------------------------------------------
# Performance knob – pick "high" unless you need bit-exact FP32.
# ---------------------------------------------------------------------
torch.set_float32_matmul_precision("high")   # enables TF32 on A2000

_MODEL_ID = "briaai/RMBG-2.0"
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# One-time model load
_model = (
    AutoModelForImageSegmentation
    .from_pretrained(_MODEL_ID, trust_remote_code=True)
    .to(_DEVICE)
    .eval()
)

_transform = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

def remove_bg(image_path: Path) -> Image.Image:
    """Return a PIL image with an alpha-matted foreground."""
    img = Image.open(image_path).convert("RGB")
    with torch.no_grad():
        mask = (
            _model(_transform(img).unsqueeze(0).to(_DEVICE))[-1]
            .sigmoid()
            .cpu()[0]
            .squeeze()
        )
    mask_pil = transforms.ToPILImage()(mask).resize(img.size)
    img.putalpha(mask_pil)
    return img
