from typing import Generic, Optional, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


def camel(snake_case: str) -> str:
    words = snake_case.split("_")
    return f"{words[0]}{''.join(word.capitalize() for word in words[1:])}"


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True)


DataT = TypeVar("DataT")


class ResponseModel(PydanticBaseModel, Generic[DataT]):
    data: Optional[DataT]
    status: int = 1
    errCode: int = 200


if __name__ == "__main__":

    class TestModel(BaseModel):
        error_code: int = 200
        error_msg: str = "success"

    print(TestModel(**{"error_code": 301, "error_msg": "balabala"}).model_dump_json())
