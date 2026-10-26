from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cargar_csv import load_fixture
from app.domain import (
    InvalidOrderTransition, InvalidOrderData, OrderItemLimitExceeded,
)
from app.specifications import discount_rate

app = FastAPI(title="TechStore U4")
orders = load_fixture()          # repositorio en memoria


# ---------- DTOs ----------
class ShipRequest(BaseModel):
    tracking_number: str


class CancelRequest(BaseModel):
    reason: str


def to_dto(order):
    return {
        "id": order.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(order.total.amount),
        "discount_rate": str(discount_rate(order)),
        "events": [e.name for e in order.events],
    }


def get_order(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no existe")
    return order


# ---------- Excepciones de dominio -> HTTP ----------
@app.exception_handler(InvalidOrderTransition)
def handle_transition(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidOrderData)
def handle_data(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(OrderItemLimitExceeded)
def handle_limit(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---------- Endpoints (controladores delgados) ----------
@app.get("/orders/{order_id}")
def read_order(order_id: str):
    return to_dto(get_order(order_id))


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = get_order(order_id)
    order.confirm()
    return to_dto(order)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipRequest):
    order = get_order(order_id)
    order.ship(body.tracking_number)
    return to_dto(order)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelRequest):
    order = get_order(order_id)
    order.cancel(body.reason)
    return to_dto(order)


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = get_order(order_id)
    order.deliver()
    return to_dto(order)


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = get_order(order_id)
    order.return_order()
    return to_dto(order)