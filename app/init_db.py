# app/init_db.py
from sqlmodel import Session
from .crud import get_engine, create_db_and_tables, add_room, add_bed
engine = get_engine("sqlite:///./pgrent.db")
create_db_and_tables(engine)
with Session(engine) as s:
    r = add_room(s,"Room 1")
    add_bed(s, r.id, 1)
    add_bed(s, r.id, 2)
    r2 = add_room(s,"Room 2")
    add_bed(s, r2.id, 1)
