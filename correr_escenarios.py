import csv
from cargar_csv import load_fixture
from app.domain import DomainException, OrderItem
from app.specifications import discount_rate


def descuento(o):
    return f"{int(discount_rate(o) * 100)}%"


def confirmar(o):
    o.confirm()


def agregar_sku003_x2(o):
    precio = o.items[0].unit_price          # precio de SKU003 ya cargado
    o.add_item(OrderItem("SKU003", 2, precio))


def confirmar_enviar_sin_guia(o):
    o.confirm()
    o.ship("")


def confirmar_dos_veces(o):
    o.confirm()
    o.confirm()


def confirmar_enviar_cancelar(o):
    o.confirm()
    o.ship("GUIA-123")
    o.cancel("Cambio de opinion")


def confirmar_enviar_devolver(o):
    o.confirm()
    o.ship("GUIA-123")
    o.return_order()


def confirmar_enviar_entregar(o):
    o.confirm()
    o.ship("GUIA-123")
    o.deliver()


# (caso, pedido, operacion, esperado, funcion)
# funcion None = solo evaluar descuento
ESCENARIOS = [
    ("E01", "O001", "evaluar_descuento", "10%", None),
    ("E02", "O002", "evaluar_descuento", "0%", None),
    ("E03", "O003", "confirmar", "rechazo", confirmar),
    ("E04", "O005", "evaluar_descuento", "0%", None),
    ("E05", "O006", "evaluar_descuento", "5%", None),
    ("E06", "O007", "confirmar", "rechazo", confirmar),
    ("E07", "O008", "confirmar", "exito", confirmar),
    ("E08", "O009", "agregar SKU003 x2", "rechazo", agregar_sku003_x2),
    ("E09", "O010", "evaluar_descuento", "0%", None),
    ("E10", "O011", "evaluar_descuento", "0%", None),
    ("E11", "O012", "confirmar y enviar sin guia", "rechazo", confirmar_enviar_sin_guia),
    ("E12", "O013", "confirmar dos veces", "rechazo", confirmar_dos_veces),
    ("E13", "O014", "confirmar, enviar y cancelar", "rechazo", confirmar_enviar_cancelar),
    ("E14", "O015", "confirmar, enviar y devolver", "exito", confirmar_enviar_devolver),
    ("E15", "O016", "confirmar, enviar y entregar", "exito", confirmar_enviar_entregar),
]

filas = []
for caso, pedido, operacion, esperado, accion in ESCENARIOS:
    o = load_fixture()[pedido]              # datos frescos para cada caso
    estado_inicial = o.status.value
    detalle = ""

    if accion is None:
        real = descuento(o)
        detalle = f"total={o.total.amount}, unidades={o.units}, VIP={o.customer.is_vip}, promo={o.has_promotion}"
    else:
        try:
            accion(o)
            real = "exito"
        except DomainException as exc:
            real = "rechazo"
            detalle = f"{type(exc).__name__}: {exc}"

    eventos = [e.name for e in o.events] or "ninguno"
    ok = "OK" if real == esperado else "REVISAR"
    filas.append([caso, pedido, estado_inicial, operacion, real,
                  o.status.value, str(eventos), detalle, ok])
    print(f"{caso} {pedido} {estado_inicial:>5} | {operacion:<30} | "
          f"{real:<8} (esperado {esperado:<7}) -> {o.status.value:<9} "
          f"eventos={eventos} {detalle} [{ok}]")

with open("bitacora_escenarios.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["caso", "pedido", "estado_inicial", "operacion", "resultado",
                "estado_final", "eventos", "detalle", "coincide"])
    w.writerows(filas)
print("\nBitácora guardada en bitacora_escenarios.csv")