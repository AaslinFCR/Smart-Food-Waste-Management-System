from pydantic import BaseModel


class StreamControl(BaseModel):
    enabled: bool
