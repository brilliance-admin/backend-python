from pydantic import BaseModel


class ChartData(BaseModel):
    data: dict
    options: dict
    width: int | None = None
    height: int = 50
    type: str = 'line'

    component_type: str = 'chart'
