import io
import base64
from typing import Optional, Literal

import requests
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from PIL import Image
import pillow_heif  # registers HEIF opener into Pillow

app = FastAPI(title="HEIC Converter")

# --- add near the top ---
from pydantic import BaseModel

class ConvertB64Body(BaseModel):
    b64: str
    format: Optional[Literal["jpg", "png"]] = "jpg"
    quality: Optional[int] = 90

# --- add after other endpoints ---
@app.post("/convert/base64")
def convert_base64(body: ConvertB64Body):
    try:
        raw = base64.b64decode(body.b64, validate=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")

    try:
        im = Image.open(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Downloaded bytes are not an image: {e}")

    fmt = "JPEG" if body.format != "png" else "PNG"
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"

    out = io.BytesIO()
    save_kwargs = {}
    if fmt == "JPEG":
        q = body.quality or 90
        q = max(1, min(100, int(q)))
        save_kwargs["quality"] = q
        save_kwargs["optimize"] = True

    try:
        im.convert("RGB").save(out, format=fmt, **save_kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")

    buf = out.getvalue()
    b64 = base64.b64encode(buf).decode("ascii")
    return {
        "mime": mime,
        "extension": "jpg" if fmt == "JPEG" else "png",
        "base64": b64,
        "data_url": f"data:{mime};base64,{b64}",
        "bytes": len(buf),
        "width": im.width,
        "height": im.height,
    }


class ConvertBody(BaseModel):
    url: str
    format: Optional[Literal["jpg", "png"]] = "jpg"
    quality: Optional[int] = 90  # only for JPG

def _download_to_bytes(url: str, timeout=30) -> bytes:
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Bubble-HEIC-Converter/1.0"})
    try:
        resp = sess.get(url, timeout=timeout, allow_redirects=True)
        if not resp.ok:
            raise HTTPException(status_code=400, detail=f"Failed to fetch file: {resp.status_code}")
        return resp.content
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Download error: {str(e)}")

@app.post("/convert/json")
def convert_json(body: ConvertBody):
    raw = _download_to_bytes(body.url)
    try:
        im = Image.open(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Not a valid HEIC/HEIF image: {str(e)}")

    fmt = "JPEG" if body.format != "png" else "PNG"
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"

    out = io.BytesIO()
    save_kwargs = {}
    if fmt == "JPEG":
        q = body.quality or 90
        q = max(1, min(100, int(q)))
        save_kwargs["quality"] = q
        save_kwargs["optimize"] = True

    try:
        im.convert("RGB").save(out, format=fmt, **save_kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    buf = out.getvalue()
    b64 = base64.b64encode(buf).decode("ascii")

    return {
        "mime": mime,
        "extension": "jpg" if fmt == "JPEG" else "png",
        "base64": b64,  # no prefix
        "data_url": f"data:{mime};base64,{b64}",
        "bytes": len(buf),
        "width": im.width,
        "height": im.height,
    }

@app.post("/convert/binary")
def convert_binary(body: ConvertBody):
    from fastapi.responses import Response
    raw = _download_to_bytes(body.url)
    try:
        im = Image.open(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Not a valid HEIC/HEIF image: {str(e)}")

    fmt = "JPEG" if body.format != "png" else "PNG"
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"

    out = io.BytesIO()
    save_kwargs = {}
    if fmt == "JPEG":
        q = body.quality or 90
        q = max(1, min(100, int(q)))
        save_kwargs["quality"] = q
        save_kwargs["optimize"] = True

    try:
        im.convert("RGB").save(out, format=fmt, **save_kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    return Response(content=out.getvalue(), media_type=mime)
