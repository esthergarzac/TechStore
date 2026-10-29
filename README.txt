## Requisitos básicos

- Python 3.11 o superior (probado con 3.13).
- Dependencias utilizadas: `fastapi`, `uvicorn`, `pytest`, `httpx`.

## Instalación del sistema

Mediante la carpeta del proyecto (contiene `app/` y `cargar_csv.py`):

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows CMD
.venv\Scripts\activate.bat
# macOS / Linux
source .venv/bin/activate

python -m pip install fastapi uvicorn pytest httpx
```

## Pasos de ejecución

- Cargar los 16 pedidos desde los CSV: `python cargar_csv.py`
- Ejecutar los 15 escenarios E01 a E15 (`bitacora_escenarios.csv`): `python correr_escenarios.py`
- Levantar la API: `uvicorn app.api:app --reload`
- Ejecutar las pruebas: `python -m pytest -v`

Cuando la API se encuentra funcionando, la documentación interactiva (swagger) se encuentra localizado en <http://127.0.0.1:8000/docs> y el contrato OpenAPI se encuentra en <http://127.0.0.1:8000/openapi.json>.

Los cambios de la API se encuentran en la memoria. Para repetir una prueba con el mismo pedido, se debe reinciar el servidor.

## Estructura 

```
app/
  __init__.py
  domain.py               **Money, Customer, OrderItem, Order, DomainEvent, excepciones
  specifications.py       **Specification con AND/OR/NOT y reglas de descuento
  api.py                  **Endpoints FastAPI y mapeo de excepciones a HTTP
tests/
  test_domain.py          **Pruebas del dominio y las Specifications
  test_api.py             **Pruebas de la API
datos/                    **clientes, productos, pedidos, detalle_pedidos y escenarios (CSV)
cargar_csv.py             **Convierte los CSV en objetos Order
correr_escenarios.py      **Ejecuta E01 a E15 y escribe la bitácora
bitacora_escenarios.csv
```

## Reglas de negocio

- **Money:** inmutable, usa `Decimal` (nunca `float`), moneda MXN y rechaza valores negativos o no finitos.
- **Límite por pedido:** máximo 20 unidades en total (suma de cantidades, no número de renglones).
- **Descuento del 10 %:** el cliente debe ser VIP, total mayor a 500 MXN, al menos 4 unidades y sin promoción activa.
- **Descuento del 5 %:** total debe ser mayor a 5000 MXN y sin promoción activa.
- **Prioridad:** si se cumplen ambas reglas, se aplica el 10 %.
- **Inventario:** el campo `existencia` es solo dentro del catálogo; no se descontará del stock.

## Máquina de estados y eventos

```
DRAFT --confirm--> CONFIRMED --ship(guía)--> SHIPPED --deliver--> DELIVERED
                       |                        |
                 cancel(motivo)           return_order
                       |                        |
                   CANCELLED                RETURNED
```

Todos los pedidos empiezan en `DRAFT`. En cada transición se valida primero, se cambia el estado después y el evento se registra al final, solo en caso si la transición resulta ser exitosa.

Transición:       Evento:               Precondiciones:
`confirm()`       `OrderConfirmed`      Estado DRAFT, con artículos y cliente activo.
`ship(guía)`      `OrderShipped`        Estado CONFIRMED y guía no vacía.
`cancel(motivo)`  `OrderCancelled`      Estado CONFIRMED y motivo no vacío.
`deliver()`       `OrderDelivered`      Estado SHIPPED.
`return_order()`  `OrderReturned`       Estado SHIPPED.

## Endpoints

Método y ruta:                        Descripción:
`GET /orders/{order_id}`              Consulta estado, unidades, total, tasa de descuento y eventos.
`POST /orders/{order_id}/confirm`     Confirma el pedido.
`POST /orders/{order_id}/ship`        Envía el pedido. Cuerpo: `{"tracking_number": "..."}`.
`POST /orders/{order_id}/cancel`      Cancela el pedido. Cuerpo: `{"reason": "..."}`.
`POST /orders/{order_id}/deliver`     Marca el pedido como entregado.
`POST /orders/{order_id}/return`      Registra la devolución.

### Códigos de respuesta

Situación:                                                                           Código:
Operación exitosa                                                                    200
Pedido no encontrado                                                                 404 Not Found
Transición de estado prohibida (`InvalidOrderTransition`)                            409 Conflict
Datos inválidos o límite excedido (`InvalidOrderData`, `OrderItemLimitExceeded`)     422 Unprocessable Entity

Los controladores son delgados: buscan el pedido, llaman al método de `Order` y devuelven el resultado. Las reglas de negocio viven en el dominio.

## Escenarios de evaluación

Los 15 casos de `datos/escenarios.csv` (E01 a E15) se ejecutan con `python correr_escenarios.py`, encargado de cargar datos nuevos para un respectivo caso y guardar el resultado obtenido en `bitacora_escenarios.csv`.

## Pruebas

```bash
python -m pytest -v
```

Resultado actual: **39 pruebas aprobadas**. Con variantes de `Money` y `OrderItem`, el límite de 20 unidades, los descuentos y su prioridad, la composición de Specifications, todas las transiciones válidas e inválidas con sus eventos, y los códigos HTTP 200, 404, 409 y 422.

Usa `python -m pytest` y no solo `pytest`, para que Python encuentre `cargar_csv` y `app` desde la carpeta del proyecto.

## Evidencias

Las capturas (como carga de pedidos, escenarios, swagger y pytest), además de la reflexión se encuentran documentados en el reporte de entrega.
