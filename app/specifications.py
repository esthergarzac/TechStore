from decimal import Decimal


class Specification:
    def is_satisfied_by(self, order):
        raise NotImplementedError

    def __and__(self, other):
        return AndSpec(self, other)

    def __or__(self, other):
        return OrSpec(self, other)

    def __invert__(self):
        return NotSpec(self)


class AndSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order)
                and self.right.is_satisfied_by(order))


class OrSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order)
                or self.right.is_satisfied_by(order))


class NotSpec(Specification):
    def __init__(self, spec):
        self.spec = spec

    def is_satisfied_by(self, order):
        return not self.spec.is_satisfied_by(order)


# ---------- Reglas concretas ----------
class MinimumAmountSpec(Specification):
    """Total ESTRICTAMENTE mayor al umbral (>, no >=)."""
    def __init__(self, threshold: Decimal):
        self.threshold = threshold

    def is_satisfied_by(self, order):
        return order.total.amount > self.threshold


class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order):
        return order.customer.is_vip


class MinimumUnitsSpec(Specification):
    """Al menos N unidades (>=)."""
    def __init__(self, minimum: int):
        self.minimum = minimum

    def is_satisfied_by(self, order):
        return order.units >= self.minimum


class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order):
        return order.has_promotion


# ---------- Reglas de descuento ----------
ten_percent = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

five_percent = (
    MinimumAmountSpec(Decimal("5000"))
    & ~ActivePromotionSpec()
)

# Combinación con OR (cumple el requisito de usar &, | y ~)
any_discount = ten_percent | five_percent


def discount_rate(order) -> Decimal:
    """Prioridad: si aplican ambas, gana el 10 %."""
    if ten_percent.is_satisfied_by(order):
        return Decimal("0.10")
    if five_percent.is_satisfied_by(order):
        return Decimal("0.05")
    return Decimal("0")