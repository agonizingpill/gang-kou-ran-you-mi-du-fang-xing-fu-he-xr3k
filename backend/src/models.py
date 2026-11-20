from decimal import Decimal
from sqlalchemy import String,Numeric,Float,Boolean,ForeignKey,Text,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(120),unique=True)
    password:Mapped[str]=mapped_column(String(256))
    role:Mapped[str]=mapped_column(String(20))
class Tank(Base):
    __tablename__='tanks'
    __table_args__=(CheckConstraint('liters >= 0'),CheckConstraint("grade IN ('VLSFO','MGO')"),CheckConstraint("status IN ('active','hold')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    grade:Mapped[str]=mapped_column(String(20))
    liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    status:Mapped[str]=mapped_column(String(20),default='active')
class FuelSample(Base):
    __tablename__='fuel_samples'
    __table_args__=(CheckConstraint('density_15 > 0 AND viscosity > 0 AND sulfur >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    tank_id:Mapped[int]=mapped_column(ForeignKey('tanks.id'))
    code:Mapped[str]=mapped_column(String(70),unique=True)
    density_15:Mapped[Decimal]=mapped_column(Numeric(10,3))
    viscosity:Mapped[Decimal]=mapped_column(Numeric(10,3))
    sulfur:Mapped[Decimal]=mapped_column(Numeric(7,4))
    log_density:Mapped[float|None]=mapped_column(Float,nullable=True)
    threshold:Mapped[float|None]=mapped_column(Float,nullable=True)
    status:Mapped[str]=mapped_column(String(20),default='received')
    retest_density:Mapped[Decimal|None]=mapped_column(Numeric(10,3),nullable=True)
    retest_note:Mapped[str]=mapped_column(Text,default='')
    reference:Mapped[bool]=mapped_column(Boolean,default=False)
    evidence:Mapped[str]=mapped_column(Text,default='')
class Transfer(Base):
    __tablename__='transfers'
    __table_args__=(CheckConstraint('liters > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(70),unique=True)
    sample_id:Mapped[int]=mapped_column(ForeignKey('fuel_samples.id'))
    liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    vessel:Mapped[str]=mapped_column(String(120))
    status:Mapped[str]=mapped_column(String(20),default='requested')
    grade_snapshot:Mapped[str]=mapped_column(String(20))
    density_snapshot:Mapped[Decimal]=mapped_column(Numeric(10,3))
    viscosity_snapshot:Mapped[Decimal]=mapped_column(Numeric(10,3))
    sulfur_snapshot:Mapped[Decimal]=mapped_column(Numeric(7,4))
    released_by:Mapped[str]=mapped_column(String(120),default='')
class Audit(Base):
    __tablename__='audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(120))
    action:Mapped[str]=mapped_column(String(60))
    detail:Mapped[str]=mapped_column(Text)
    at:Mapped[str]=mapped_column(String(40))
