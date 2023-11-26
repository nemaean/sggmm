from pathlib import Path
from pydantic import BaseModel


class Mod(BaseModel):
    source: Path
    data: str
