from src.common import BaseModel


class ShareDataSchema(BaseModel):
    """token response class"""

    text: str
    size: int = 0
    exp_style: str
    exp_value: int
    type: str
    name: str
    key: str
