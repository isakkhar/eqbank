# filters.py
from django import template
register = template.Library()

@register.filter
def to_bangla_number(value):
    numbers = {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'৭','8':'৮','9':'৯'}
    return ''.join(numbers.get(ch, ch) for ch in str(value))
