"""Monetary field-boundary helpers, not a tax calculator or blanket rate rounding.

See references/filing-handoff.md. Preserve source cents; round only when a dollar
amount reaches a form field. Transfers reuse that resulting filing value.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _decimal(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError('Use a decimal string or Decimal, not a float or integer')
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal amount') from exc
    if not amount.is_finite():
        raise ValueError('Money must be finite')
    return amount


def form_dollars(value):
    """Round ONE monetary field half-up; keep null unknown and remove -0."""
    if value is None:
        return None
    try:
        rounded = _decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError('Amount exceeds supported decimal precision') from exc
    return '0' if rounded == 0 else format(rounded, 'f')


def _amounts(values):
    if not isinstance(values, (list, tuple)):
        raise ValueError('Supply a list or tuple of monetary amounts')
    # Validate known amounts even if another operand is unknown.
    return [None if value is None else _decimal(value) for value in values]


def source_sum_to_form(values):
    """Aggregate source cents for ONE entry field, then round the total once."""
    amounts = _amounts(values)
    if any(value is None for value in amounts):
        return None
    return form_dollars(sum(amounts, Decimal(0)))


def sum_form_dollars(values):
    """Sum previously rounded form fields; refuse raw fractional operands."""
    amounts = _amounts(values)
    if any(value is not None and value != value.to_integral_value() for value in amounts):
        raise ValueError('Round each monetary form field before summing form values')
    if any(value is None for value in amounts):
        return None
    return form_dollars(sum(amounts, Decimal(0)))
