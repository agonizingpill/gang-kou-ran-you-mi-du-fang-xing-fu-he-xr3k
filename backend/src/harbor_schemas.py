from datetime import datetime,date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
class Clean(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class LineInput(Clean):
    code:str=Field(min_length=2,max_length=40)
    allowed_grade:Literal['VLSFO','MGO']
    capacity_lpm:Decimal=Field(gt=0,le=10000,max_digits=12,decimal_places=3)
    min_flush_liters:Decimal=Field(gt=0,le=10000,max_digits=12,decimal_places=3)
class PermitValues(Clean):
    line_id:int=Field(gt=0)
    flush_liters:Decimal=Field(ge=0,le=100000,max_digits=12,decimal_places=3)
    clean_grade:Literal['VLSFO','MGO']
class PermitInput(PermitValues):transfer_id:int=Field(gt=0)
class Completion(Clean):completion_note:str=Field(min_length=8,max_length=600)
class BerthInput(Clean):
    code:str=Field(min_length=2,max_length=40)
    max_draft:Decimal=Field(gt=0,le=30,max_digits=8,decimal_places=3)
class WindowValues(Clean):
    berth_id:int=Field(gt=0)
    starts_at:datetime
    ends_at:datetime
    draft:Decimal=Field(gt=0,le=30,max_digits=8,decimal_places=3)
class WindowInput(WindowValues):transfer_id:int=Field(gt=0)
class RetainedInput(Clean):
    transfer_id:int=Field(gt=0)
    seal_code:str=Field(min_length=4,max_length=70)
    retained_ml:int=Field(ge=500,le=5000)
    storage_until:date
class RetestInput(Clean):
    retained_id:int=Field(gt=0)
    reason:str=Field(min_length=8,max_length=600)
    lab:str=Field(min_length=2,max_length=120)
class RetestResult(Clean):
    result_density:Decimal=Field(ge=700,le=1100,max_digits=10,decimal_places=3)
    result_note:str=Field(min_length=8,max_length=600)
class RetestClose(Clean):closure_note:str=Field(default='',max_length=600)
