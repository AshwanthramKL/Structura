from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Structura Extractor")

class ExtractResponse(BaseModel):
    ok: bool
    data: dict
    confidence: float

@app.post("/extract", response_model=ExtractResponse)
async def extract(file: UploadFile):
    # TODO: wire pipeline
    return ExtractResponse(ok=True, data={}, confidence=0.0)
