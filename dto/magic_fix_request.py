from pydantic import BaseModel
from typing import Optional

class MagicFixRequest(BaseModel):
    inputImagePath: str
    inputMaskImagePath: str
    inputGeneratedImagePath: str
    outputFileName: str
