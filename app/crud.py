# app/crud.py
from sqlmodel import Session, select
from .models import Room, Bed, Person, Payment, ElectricityBill
from datetime import datetime
from typing import Optional
from sqlmodel import create_engine
from sqlmodel import SQLModel


def get_engine(db_path: str = "sqlite:///./pgrent.db"):
    return create_engine(db_path, connect_args={"check_same_thread": False})

def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)

# Room / bed helpers
def get_rooms(session: Session):
    return session.exec(select(Room)).all()

def get_room(session: Session, room_id: int):
    return session.get(Room, room_id)

def add_room(session: Session, name: str):
    room = Room(name=name)
    session.add(room); session.commit(); session.refresh(room)
    return room

def add_bed(session: Session, room_id:int, bed_number:int):
    bed = Bed(room_id=room_id, bed_number=bed_number, vacant=True)
    session.add(bed); session.commit(); session.refresh(bed)
    return bed

# person
def add_person(session: Session, name, id_proof, room_id, bed_id, base_rent):
    # mark bed as occupied
    bed = session.get(Bed, bed_id)
    if not bed:
        raise ValueError("Invalid bed_id")
    if not bed.vacant:
        raise ValueError("Bed is already occupied")
    bed.vacant = False
    
    p = Person(name=name, id_proof=id_proof, room_id=room_id, bed_id=bed_id, base_rent=base_rent)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def get_person(session: Session, person_id:int):
    return session.get(Person, person_id)

def list_people(session: Session):
    return session.exec(select(Person)).all()

# payments
def add_payment(session: Session, person_id:int, amount:float, month:Optional[str]=None):
    pay = Payment(person_id=person_id, amount=amount, month=month)
    session.add(pay); session.commit(); session.refresh(pay)
    return pay

def get_payments_for_person(session: Session, person_id:int):
    return session.exec(select(Payment).where(Payment.person_id==person_id).order_by(Payment.timestamp)).all()

# electricity
def add_eb(session: Session, room_id:int, month:str, total_amount:float, split_evenly:bool=True):
    eb = ElectricityBill(room_id=room_id, month=month, total_amount=total_amount, split_evenly=split_evenly)
    session.add(eb); session.commit(); session.refresh(eb)
    return eb

def get_eb_for_room_month(session: Session, room_id:int, month:str):
    return session.exec(select(ElectricityBill).where(ElectricityBill.room_id==room_id).where(ElectricityBill.month==month)).one_or_none()

# compute due for a person for a given month
def compute_due_for_person(session: Session, person_id:int, month:Optional[str]=None):
    p = get_person(session, person_id)
    if not p:
        return None
    # base rent
    rent = p.base_rent
    eb_share = 0.0
    if month:
        eb = get_eb_for_room_month(session, p.room_id, month)
        if eb:
            if not eb.split_evenly:
                # whole EB assigned to room (owner may decide), but we will apply whole eb to the bed if split_evenly False
                eb_share = eb.total_amount
            else:
                # split among non-vacant beds in that room
                beds = session.exec(select(Bed).where(Bed.room_id==p.room_id)).all()
                occupied_beds = [b for b in beds if not b.vacant]
                count = max(1, len(occupied_beds))
                eb_share = eb.total_amount / count
    # sum payments in this month if month provided, else all payments
    if month:
        payments = session.exec(select(Payment).where(Payment.person_id==person_id).where(Payment.month==month)).all()
    else:
        payments = get_payments_for_person(session, person_id)
    paid = sum([pay.amount for pay in payments])
    total_due = rent + eb_share - paid
    return {
        "rent": rent,
        "eb_share": eb_share,
        "paid": paid,
        "due": round(total_due, 2),
        "person": p
    }
 
