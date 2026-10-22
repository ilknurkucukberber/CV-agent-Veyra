from pydantic import BaseModel, ConfigDict


class APISchema(BaseModel):
    """Tüm şemaların taban sınıfı."""


class ORMSchema(APISchema):
    """ORM nesnelerinden (from_attributes) üretilen response şemaları için."""

    model_config = ConfigDict(from_attributes=True)
