from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="MeloTTS Local Service", version="1.0")
_lock = threading.Lock()
_models: dict[str, object] = {}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "ZH"
    speaker: str = ""
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "melotts", "device": os.getenv("MELOTTS_DEVICE", "auto")}


@app.post("/tts")
def tts(payload: TTSRequest) -> Response:
    try:
        from melo.api import TTS
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MeloTTS 未安装或导入失败：{exc}") from exc
    language = payload.language.upper()
    with _lock:
        model = _models.get(language)
        if model is None:
            model = TTS(language=language, device=os.getenv("MELOTTS_DEVICE", "auto"))
            _models[language] = model
        speaker_ids = model.hps.data.spk2id
        speaker_keys = list(speaker_ids.keys())
        speaker = payload.speaker or speaker_keys[0]
        if speaker not in speaker_keys:
            speaker = speaker_keys[0]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            output = Path(handle.name)
        try:
            model.tts_to_file(payload.text, speaker_ids[speaker], str(output), speed=payload.speed)
            data = output.read_bytes()
        finally:
            output.unlink(missing_ok=True)
    if len(data) < 200:
        raise HTTPException(status_code=500, detail="MeloTTS 没有生成有效音频")
    return Response(content=data, media_type="audio/wav")
