import dataclasses
from decimal import Decimal

import pytest

from cargar_csv import load_fixture
from app.domain import (
    Customer, DomainEvent, InvalidOrderData, InvalidOrderTransition,
    Money, Order, OrderItem, OrderItemLimitExceeded, OrderStatus,
)
from app.specifications import (
    ActivePromotionSpec, MinimumAmountSpec, VIPCustomerSpec,
    discount_rate, five_percent, ten_percent,
)


@pytest.fixture
def orders():
    return load_fixture()


# ---------- Money ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


@pytest.mark.parametrize("valor", ["NaN", "Infinity"])
def test_money_no_finito(valor):
    with pytest.raises(InvalidOrderData):
        Money(Decimal(valor))


def test_money_es_inmutable():
    m = Money(Decimal("10"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.amount = Decimal("20")


def test_money_add_devuelve_nuevo_objeto():
    a, b = Money(Decimal("100")), Money(Decimal("50"))
    assert a.add(b) == Money(Decimal("150"))
    assert a.amount == Decimal("100")


def test_money_add_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1"), "MXN").add(Money(Decimal("1"), "USD"))


# ---------- OrderItem ----------
@pytest.mark.parametrize("cantidad", [0, -1])
def test_item_cantidad_invalida(cantidad):
    with pytest.raises(InvalidOrderData):
        OrderItem("SKU001", cantidad, Money(Decimal("10")))


# ---------- Carga de datos ----------
def test_pedido_o001_inicia_draft(orders):
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


def test_son_16_pedidos_todos_draft(orders):
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


# ---------- Límite de 20 unidades ----------
def test_21_unidades_excede_limite(orders):
    o = orders["O009"]                       # tiene 19 unidades
    precio = o.items[0].unit_price
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, precio))
    assert o.units == 19                     # no modificó items


def test_20_unidades_exactas_permitidas(orders):
    assert orders["O008"].units == 20


def test_limite_cuenta_unidades_no_renglones():
    o = Order(Customer("C"), "X")
    for _ in range(3):
        o.add_item(OrderItem("SKU001", 6, Money(Decimal("1"))))
    assert o.units == 18
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU002", 3, Money(Decimal("1"))))


def test_no_se_agregan_items_despues_de_confirmar(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("1"))))


# ---------- Confirmar ----------
def test_confirmar_cliente_inactivo(orders):
    o = orders["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT
    assert o.events == []


def test_confirmar_pedido_vacio(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT
    assert o.events == []


def test_confirmar_20_unidades(orders):
    o = orders["O008"]
    o.confirm()
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_confirmacion_doble(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert o.status == OrderStatus.CONFIRMED
    assert len(o.events) == 1                # el segundo no agregó evento


# ---------- Descuentos y Specifications ----------
@pytest.mark.parametrize("pedido,tasa", [
    ("O001", "0.10"),   # VIP, >500, 4 unidades, sin promo
    ("O002", "0"),      # no VIP
    ("O005", "0"),      # promoción activa
    ("O006", "0.05"),   # total > 5000
    ("O010", "0"),      # total exactamente 500
    ("O011", "0"),      # solo 3 unidades
])
def test_descuentos(orders, pedido, tasa):
    assert discount_rate(orders[pedido]) == Decimal(tasa)


def test_prioridad_10_sobre_5():
    o = Order(Customer("V", is_vip=True), "P")
    o.add_item(OrderItem("SKU001", 4, Money(Decimal("2000"))))   # 8000
    assert ten_percent.is_satisfied_by(o)
    assert five_percent.is_satisfied_by(o)
    assert discount_rate(o) == Decimal("0.10")


def test_umbral_estricto(orders):
    assert not MinimumAmountSpec(Decimal("500")).is_satisfied_by(orders["O010"])


def test_composicion_or_y_not(orders):
    o = orders["O005"]                       # promoción activa
    assert ActivePromotionSpec().is_satisfied_by(o)
    assert not (~ActivePromotionSpec()).is_satisfied_by(o)
    assert (VIPCustomerSpec() | ActivePromotionSpec()).is_satisfied_by(o)


def test_specification_no_modifica_el_pedido(orders):
    o = orders["O001"]
    ten_percent.is_satisfied_by(o)
    assert o.status == OrderStatus.DRAFT and o.events == []


# ---------- Envío, cancelación, entrega, devolución ----------
@pytest.mark.parametrize("guia", ["", "   ", None])
def test_enviar_sin_guia(orders, guia):
    o = orders["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship(guia)
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_enviar_desde_draft(orders):
    with pytest.raises(InvalidOrderTransition):
        orders["O012"].ship("G1")


def test_cancelar_desde_shipped(orders):
    o = orders["O014"]
    o.confirm()
    o.ship("G1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("Cambio de opinion")
    assert o.status == OrderStatus.SHIPPED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]


def test_cancelar_sin_motivo(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.cancel("  ")
    assert o.status == OrderStatus.CONFIRMED


def test_cancelar_desde_confirmed(orders):
    o = orders["O013"]
    o.confirm()
    o.cancel("Cliente lo pidio")
    assert o.status == OrderStatus.CANCELLED
    assert o.events[-1].name == "OrderCancelled"


def test_flujo_entrega(orders):
    o = orders["O016"]
    o.confirm(); o.ship("G1"); o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert [e.name for e in o.events] == [
        "OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_devolucion(orders):
    o = orders["O015"]
    o.confirm(); o.ship("G1"); o.return_order()
    assert o.status == OrderStatus.RETURNED
    assert [e.name for e in o.events] == [
        "OrderConfirmed", "OrderShipped", "OrderReturned"]


def test_entregar_desde_confirmed(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.deliver()


# ---------- Eventos ----------
def test_evento_es_inmutable(orders):
    o = orders["O013"]
    o.confirm()
    evento = o.events[0]
    assert isinstance(evento, DomainEvent) and evento.order_id == "O013"
    with pytest.raises(dataclasses.FrozenInstanceError):
        evento.name = "Otro"