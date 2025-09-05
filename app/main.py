from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
import os
from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlmodel import select

from .models import Room, Payment, SQLModel, create_engine
from .crud import (
    get_engine, create_db_and_tables, get_rooms, add_room,
    add_bed, add_person, list_people, get_person,
    add_payment, add_eb, compute_due_for_person
)

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

engine = get_engine("sqlite:///./pgrent.db")
create_db_and_tables(engine)

# simple index: show rooms, people
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with Session(engine) as session:
        rooms = get_rooms(session)
        people = list_people(session)
    return templates.TemplateResponse("index.html", {"request": request, "rooms": rooms, "people": people})

@app.post("/rooms/add")
def rooms_add(name: str = Form(...)):
    with Session(engine) as session:
        add_room(session, name)
    return RedirectResponse("/", status_code=303)

@app.post("/beds/add")
def beds_add(room_id: int = Form(...), bed_number: int = Form(...)):
    with Session(engine) as session:
        add_bed(session, room_id, int(bed_number))
    return RedirectResponse("/", status_code=303)

@app.get("/person/add", response_class=HTMLResponse)
def person_add_form(request: Request):
    with Session(engine) as session:
        rooms = get_rooms(session)
    return templates.TemplateResponse("add_person.html", {"request": request, "rooms": rooms})

@app.post("/person/add")
def person_add(name: str = Form(...), id_proof: str = Form(""), room_id: int = Form(...), bed_id: int = Form(...), base_rent: float = Form(0.0)):
    with Session(engine) as session:
        add_person(session, name, id_proof, int(room_id), int(bed_id), float(base_rent))
    return RedirectResponse("/", status_code=303)

@app.get("/room/{room_id}", response_class=HTMLResponse)
def view_room(request: Request, room_id: int):
    with Session(engine) as session:
        room = session.exec(
            select(Room).where(Room.id == room_id).options(selectinload(Room.beds))
        ).first()
        if not room:
            return HTMLResponse(f"Room {room_id} not found", status_code=404)
    return templates.TemplateResponse("room.html", {"request": request, "room": room})

@app.post("/room/{room_id}/eb/upload")
def upload_eb(room_id: int, month: str = Form(...), total_amount: float = Form(...), split_evenly: str = Form("yes")):
    split = (split_evenly.lower() in ["yes", "true", "1"])
    with Session(engine) as session:
        add_eb(session, room_id, month, float(total_amount), split)
    return RedirectResponse(f"/room/{room_id}", status_code=303)

@app.get("/person/{person_id}", response_class=HTMLResponse)
def person_detail(request: Request, person_id: int, month: str = None):
    with Session(engine) as session:
        data = compute_due_for_person(session, person_id, month)
        payments = session.exec(
            Payment.select().where(Payment.person_id == person_id)
        ).all()
    return templates.TemplateResponse("person.html", {"request": request, "data": data, "payments": payments, "month": month})

@app.post("/person/{person_id}/pay")
def person_pay(person_id: int, amount: float = Form(...), month: str = Form(None)):
    with Session(engine) as session:
        add_payment(session, person_id, float(amount), month)
    return RedirectResponse(f"/person/{person_id}?month={month or ''}", status_code=303)

@app.post("/person/{person_id}/pay_full")
def pay_full(person_id: int, month: str = Form(None)):
    with Session(engine) as session:
        info = compute_due_for_person(session, person_id, month)
        if info:
            amount = max(info["due"], 0)
            add_payment(session, person_id, float(amount), month)
    return RedirectResponse(f"/person/{person_id}?month={month or ''}", status_code=303)

# API endpoint
@app.get("/api/person/{person_id}")
def api_person(person_id: int, month: str = None):
    with Session(engine) as session:
        info = compute_due_for_person(session, person_id, month)
    if not info:
        return JSONResponse({"error": "Person not found"}, status_code=404)
    return {
        "rent": info["rent"],
        "eb_share": info["eb_share"],
        "paid": info["paid"],
        "due": info["due"],
        "person": {"id": info["person"].id, "name": info["person"].name}
    }
