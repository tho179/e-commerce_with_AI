from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def vnd(value):
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")

    rounded = int(amount.quantize(Decimal("1")))
    formatted = f"{rounded:,}".replace(",", ".")
    return f"{formatted} VNĐ"
