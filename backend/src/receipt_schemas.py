from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
class CleanInput(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class CapacityIn(CleanInput):
    tank_id:int=Field(gt=0)
    capacity_liters:Decimal=Field(gt=0,le=100000000,max_digits=14,decimal_places=3)
    density_15:Decimal=Field(gt=0,le=1500,max_digits=10,decimal_places=3)
    baseline_note:str=Field(min_length=8,max_length=600)
class ReceiptValues(CleanInput):
    grade:Literal['VLSFO','MGO']
    liters:Decimal=Field(gt=0,le=100000000,max_digits=14,decimal_places=3)
    density_15:Decimal=Field(gt=0,le=1500,max_digits=10,decimal_places=3)
    viscosity:Decimal=Field(gt=0,le=1000,max_digits=10,decimal_places=3)
    sulfur:Decimal=Field(ge=0,le=5,max_digits=7,decimal_places=4)
class ReceiptIn(ReceiptValues):
    code:str=Field(min_length=2,max_length=70)
    tank_id:int=Field(gt=0)
class ReconciliationIn(CleanInput):
    transfer_id:int=Field(gt=0)
    meter_before:Decimal=Field(ge=0,le=100000000,max_digits=14,decimal_places=3)
    meter_after:Decimal=Field(ge=0,le=100000000,max_digits=14,decimal_places=3)
    vessel_received_liters:Decimal=Field(gt=0,le=100000000,max_digits=14,decimal_places=3)
class Investigation(CleanInput):
    investigation:str=Field(min_length=8,max_length=600)
