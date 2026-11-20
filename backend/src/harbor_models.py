from decimal import Decimal
from sqlalchemy import String,Numeric,ForeignKey,JSON,Integer,Boolean,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class FuelLine(Base):
    __tablename__='fuel_lines'
    __table_args__=(CheckConstraint('capacity_lpm > 0 AND min_flush_liters > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    allowed_grade:Mapped[str]=mapped_column(String(20))
    capacity_lpm:Mapped[Decimal]=mapped_column(Numeric(12,3))
    min_flush_liters:Mapped[Decimal]=mapped_column(Numeric(12,3))
    state:Mapped[str]=mapped_column(String(20),default='idle')
class LinePermit(Base):
    __tablename__='line_permits'
    id:Mapped[int]=mapped_column(primary_key=True)
    transfer_id:Mapped[int]=mapped_column(ForeignKey('transfers.id'),unique=True)
    line_id:Mapped[int]=mapped_column(ForeignKey('fuel_lines.id'))
    flush_liters:Mapped[Decimal]=mapped_column(Numeric(12,3))
    clean_grade:Mapped[str]=mapped_column(String(20))
    state:Mapped[str]=mapped_column(String(20),default='planned')
    approved_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    release_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    completion_note:Mapped[str]=mapped_column(String(600),default='')
class Berth(Base):
    __tablename__='berths'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    max_draft:Mapped[Decimal]=mapped_column(Numeric(8,3))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
class VesselWindow(Base):
    __tablename__='vessel_windows'
    id:Mapped[int]=mapped_column(primary_key=True)
    transfer_id:Mapped[int]=mapped_column(ForeignKey('transfers.id'),unique=True)
    berth_id:Mapped[int]=mapped_column(ForeignKey('berths.id'))
    starts_at:Mapped[str]=mapped_column(String(40))
    ends_at:Mapped[str]=mapped_column(String(40))
    draft:Mapped[Decimal]=mapped_column(Numeric(8,3))
    state:Mapped[str]=mapped_column(String(20),default='planned')
    confirmed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    release_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
class RetainedSample(Base):
    __tablename__='retained_samples'
    id:Mapped[int]=mapped_column(primary_key=True)
    transfer_id:Mapped[int]=mapped_column(ForeignKey('transfers.id'),unique=True)
    seal_code:Mapped[str]=mapped_column(String(70),unique=True)
    retained_ml:Mapped[int]=mapped_column(Integer)
    storage_until:Mapped[str]=mapped_column(String(10))
    state:Mapped[str]=mapped_column(String(20),default='sealed')
    transfer_snapshot:Mapped[dict]=mapped_column(JSON)
class RetestOrder(Base):
    __tablename__='retest_orders'
    id:Mapped[int]=mapped_column(primary_key=True)
    retained_id:Mapped[int]=mapped_column(ForeignKey('retained_samples.id'))
    reason:Mapped[str]=mapped_column(String(600))
    lab:Mapped[str]=mapped_column(String(120))
    result_density:Mapped[Decimal|None]=mapped_column(Numeric(10,3),nullable=True)
    out_of_spec:Mapped[bool]=mapped_column(Boolean,default=False)
    result_note:Mapped[str]=mapped_column(String(600),default='')
    state:Mapped[str]=mapped_column(String(20),default='commissioned')
    commissioned_by:Mapped[str]=mapped_column(String(120))
    closure_note:Mapped[str]=mapped_column(String(600),default='')
    result_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
