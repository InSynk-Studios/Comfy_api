from pydantic import BaseModel
from typing import Optional

class ProductBackgroundChangeRequest(BaseModel):
    prompt: str
    inputProductImagePath: str
    backgroundRefImagePath: str
    inputBlackAndWhiteImagePath: str
    inputFocusImagePath: str
    outputFileName: str
    renderStrength: float
    seed: Optional[int] = None
    