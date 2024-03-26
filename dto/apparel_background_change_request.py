from pydantic import BaseModel
from typing import Optional

class BackgroundLora(BaseModel):
    name: str
    strength_model: int
    strength_clip: int

class ApparelBackgroundChangeRequest(BaseModel):
    positivePrompt: str
    negativePrompt: str
    backgroundLora: Optional[BackgroundLora] = None
    inputImagePath: str
    inputMaskImagePath: str
    inputFocusImagePath: str
    faceDetailerPrompt: str
    outputFileName: str
    outputCount: Optional[int] = 1
    seed: Optional[int] = None