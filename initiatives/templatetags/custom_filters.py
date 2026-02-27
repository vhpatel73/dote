from django import template

register = template.Library()

@register.filter
def compact_number(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B".replace('.0B', 'B')
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace('.0M', 'M')
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K".replace('.0K', 'K')
    return f"{value:g}"
