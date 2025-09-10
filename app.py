from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pillow_heif import register_heif_opener
from PIL import Image, ImageOps
import base64, io

# Enable HEIC/HEIF support in Pillow
register_heif_opener()

app = FastAPI(title="HEIC/HEIF → JPG")

class Payload(BaseModel):
    base64: str                   # input HEIC/HEIF as base64 (with or without data URL prefix)
    quality: int | None = 90      # optional JPEG quality override

def _decode_base64(b64: str) -> bytes:
    # Accept both raw base64 and data URLs like 'data:image/heic;base64,....'
    if "," in b64 and "base64" in b64.split(",")[0].lower():
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 input.")

@app.post("/convert")
def convert(payload: Payload):
    src_bytes = _decode_base64(payload.base64)

    # Try to open via Pillow; HEIC/HEIF is handled by pillow-heif plugin.
    try:
        im = Image.open(io.BytesIO(src_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unsupported or corrupt image ({e}).")

    # Honor EXIF orientation if present.
    im = ImageOps.exif_transpose(im)

    # Ensure 3-channel RGB for JPEG
    if im.mode != "RGB":
        im = im.convert("RGB")

    out = io.BytesIO()
    # Reasonable defaults; tweak if you want smaller files
    im.save(out, format="JPEG",
            quality=int(payload.quality or 90),
            optimize=True)
    out.seek(0)
    out_b64 = base64.b64encode(out.getvalue()).decode("ascii")
    return {"base64": out_b64}
