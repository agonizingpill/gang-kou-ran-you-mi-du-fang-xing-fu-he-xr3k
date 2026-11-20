from datetime import datetime,timezone
from decimal import Decimal
from sqlalchemy import String,Numeric,Float,Boolean,ForeignKey,JSON,Text,Integer,UniqueConstraint,CheckConstraint,Index
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base

def now_iso():return datetime.now(timezone.utc).isoformat()
class BlindSession(Base):
    __tablename__='blind_sessions'
    __table_args__=(CheckConstraint("state IN ('open','sealed','scoring','revealed')"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    title:Mapped[str]=mapped_column(String(200))
    state:Mapped[str]=mapped_column(String(20),default='open')
    sealed_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    revealed_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    sealed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    revealed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    # 封卷时冻结各等级参考样编号与密度，拟合只用这份快照
    reference_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    last_scored_sample_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    score_error:Mapped[str]=mapped_column(Text,default='')
    summary_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
class BlindSample(Base):
    __tablename__='blind_samples'
    __table_args__=(UniqueConstraint('session_id','blind_code'),CheckConstraint("grade IN ('VLSFO','MGO')"),CheckConstraint("human_verdict IN ('normal','anomaly')"),CheckConstraint('density_15 > 0'))
    id:Mapped[int]=mapped_column(primary_key=True)
    session_id:Mapped[int]=mapped_column(ForeignKey('blind_sessions.id'))
    blind_code:Mapped[str]=mapped_column(String(40))
    grade:Mapped[str]=mapped_column(String(20))
    # 揭榜前封存字段：人工判定、判定依据、考样密度均不回传化验员
    density_15:Mapped[Decimal]=mapped_column(Numeric(10,3))
    human_verdict:Mapped[str]=mapped_column(String(20))
    human_basis:Mapped[str]=mapped_column(String(600),default='')
class BlindReading(Base):
    __tablename__='blind_readings'
    __table_args__=(UniqueConstraint('sample_id'),Index('ix_blind_readings_accepted_at','accepted_at'))
    id:Mapped[int]=mapped_column(primary_key=True)
    sample_id:Mapped[int]=mapped_column(ForeignKey('blind_samples.id'))
    density_read:Mapped[Decimal]=mapped_column(Numeric(10,3))
    chemist:Mapped[str]=mapped_column(String(120))
    accepted_at:Mapped[str]=mapped_column(String(40),default=now_iso)
    # 收卷（封卷）后才受理的读数单列，不参与计分
    late:Mapped[bool]=mapped_column(Boolean,default=False)
    attempts:Mapped[int]=mapped_column(Integer,default=1)
class BlindScore(Base):
    __tablename__='blind_scores'
    __table_args__=(UniqueConstraint('sample_id'),CheckConstraint("outcome IN ('correct','hit','miss','false_alarm','missing','late','noscore')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    sample_id:Mapped[int]=mapped_column(ForeignKey('blind_samples.id'),unique=True)
    session_id:Mapped[int]=mapped_column(ForeignKey('blind_sessions.id'))
    grade:Mapped[str]=mapped_column(String(20))
    used_density:Mapped[Decimal|None]=mapped_column(Numeric(10,3),nullable=True)
    kde_score:Mapped[float|None]=mapped_column(Float,nullable=True)
    kde_threshold:Mapped[float|None]=mapped_column(Float,nullable=True)
    algo_verdict:Mapped[str|None]=mapped_column(String(20),nullable=True)
    human_verdict:Mapped[str]=mapped_column(String(20))
    outcome:Mapped[str]=mapped_column(String(20))
    evidence:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    scored_at:Mapped[str]=mapped_column(String(40),default=now_iso)
