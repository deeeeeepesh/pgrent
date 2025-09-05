# app/models.py
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session, select

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    beds: List["Bed"] = Relationship(back_populates="room")
    ebs: List["ElectricityBill"] = Relationship(back_populates="room")


class Bed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bed_number: int  # 1..3
    room_id: int = Field(foreign_key="room.id")
    vacant: bool = Field(default=False)

    room: Optional[Room] = Relationship(back_populates="beds")
    person: Optional["Person"] = Relationship(back_populates="bed", sa_relationship_kwargs={"uselist": False})


class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    id_proof: Optional[str] = None
    room_id: int = Field(foreign_key="room.id")
    bed_id: int = Field(foreign_key="bed.id")
    base_rent: float = 0.0

    bed: Optional[Bed] = Relationship(back_populates="person")


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="person.id")
    amount: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    month: Optional[str] = None  # e.g. '2025-06' for reference


class ElectricityBill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="room.id")
    month: str  # 'YYYY-MM'
    total_amount: float
    split_evenly: bool = Field(default=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    room: Optional[Room] = Relationship(back_populates="ebs")
