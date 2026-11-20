from typing import Literal
from decimal import Decimal
from pydantic import BaseModel,Field,ConfigDict
class Clean(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class SessionIn(Clean):
    code:str=Field(min_length=2,max_length=60)
    title:str=Field(min_length=4,max_length=200)
class SampleIn(Clean):
    blind_code:str=Field(min_length=2,max_length=40)
    grade:Literal['VLSFO','MGO']
    density_15:Decimal=Field(ge=700,le=1100,max_digits=10,decimal_places=3)
    human_verdict:Literal['normal','anomaly']
    human_basis:str=Field(default='',max_length=600)
class ReadingIn(Clean):
    blind_code:str=Field(min_length=2,max_length=40)
    density_read:Decimal=Field(ge=700,le=1100,max_digits=10,decimal_places=3)
