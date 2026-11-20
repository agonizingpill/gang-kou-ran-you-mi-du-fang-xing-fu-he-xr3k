from pydantic import BaseModel,Field
from decimal import Decimal
from typing import Literal
class Login(BaseModel):
    email:str
    password:str
class TankIn(BaseModel):
    code:str=Field(min_length=2,max_length=60)
    grade:Literal['VLSFO','MGO']
    liters:Decimal=Field(gt=0,le=100000000,max_digits=14,decimal_places=3)
class TankState(BaseModel):status:Literal['active','hold']
class SampleIn(BaseModel):
    code:str=Field(min_length=2,max_length=70)
    tank_id:int
    density_15:Decimal=Field(gt=0,le=1500,max_digits=10,decimal_places=3)
    viscosity:Decimal=Field(gt=0,le=1000,max_digits=10,decimal_places=3)
    sulfur:Decimal=Field(ge=0,le=5,max_digits=7,decimal_places=4)
class RetestIn(BaseModel):
    density:Decimal=Field(gt=0,le=1500,max_digits=10,decimal_places=3)
    note:str=Field(min_length=8,max_length=2000)
class TransferIn(BaseModel):
    code:str=Field(min_length=2,max_length=70)
    sample_id:int
    liters:Decimal=Field(gt=0,le=100000000,max_digits=14,decimal_places=3)
    vessel:str=Field(min_length=2,max_length=120)
