"""Arrival receipts and custody reconciliations preserve independent volume evidence."""
from decimal import Decimal
from sqlalchemy import String,Numeric,ForeignKey,JSON,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class TankCapacity(Base):
    __tablename__='tank_capacities'
    __table_args__=(CheckConstraint('capacity_liters > 0 AND density_15 > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    tank_id:Mapped[int]=mapped_column(ForeignKey('tanks.id'),unique=True)
    capacity_liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    density_15:Mapped[Decimal]=mapped_column(Numeric(10,3))
    baseline_note:Mapped[str]=mapped_column(String(600))
class TankReceipt(Base):
    __tablename__='tank_receipts'
    __table_args__=(CheckConstraint('liters > 0 AND density_15 > 0 AND viscosity > 0 AND sulfur >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    tank_id:Mapped[int]=mapped_column(ForeignKey('tanks.id'))
    code:Mapped[str]=mapped_column(String(70),unique=True)
    grade:Mapped[str]=mapped_column(String(20))
    liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    density_15:Mapped[Decimal]=mapped_column(Numeric(10,3))
    viscosity:Mapped[Decimal]=mapped_column(Numeric(10,3))
    sulfur:Mapped[Decimal]=mapped_column(Numeric(7,4))
    state:Mapped[str]=mapped_column(String(20),default='planned')
    inspection_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    receipt_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    received_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
class LoadingReconciliation(Base):
    __tablename__='loading_reconciliations'
    __table_args__=(CheckConstraint('meter_before >= 0 AND meter_after > meter_before AND vessel_received_liters > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    transfer_id:Mapped[int]=mapped_column(ForeignKey('transfers.id'),unique=True)
    meter_before:Mapped[Decimal]=mapped_column(Numeric(14,3))
    meter_after:Mapped[Decimal]=mapped_column(Numeric(14,3))
    vessel_received_liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    meter_liters:Mapped[Decimal]=mapped_column(Numeric(14,3))
    meter_variance_pct:Mapped[Decimal]=mapped_column(Numeric(18,4))
    vessel_variance_pct:Mapped[Decimal]=mapped_column(Numeric(18,4))
    tolerance_pct:Mapped[Decimal]=mapped_column(Numeric(6,3),default=1)
    investigation:Mapped[str]=mapped_column(String(600),default='')
    state:Mapped[str]=mapped_column(String(30))
    transfer_snapshot:Mapped[dict]=mapped_column(JSON)
    closure_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    closed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
