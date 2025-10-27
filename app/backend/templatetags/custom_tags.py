from django import template

register = template.Library()


@register.simple_tag
def toggle_sort(current_sort, current_order, column):
    """
    Zmienia kierunek sortowania dla danej kolumny.
    - Jeśli kolumna jest aktualnie posortowana rosnąco: zmienia na malejąco
    - Jeśli jest inna lub nijak nie ustawiona: ustawia rosnąco
    """

    # Jeśli obecnie sortujemy po tej samej kolumnie:
    if current_sort == column:
        return 'asc' if current_order == 'desc' else 'desc'
    # Dla nowej kolumny domyślnie sortuj rosnąco
    return 'asc'


@register.simple_tag
def sort_arrow(current_sort, current_order, column):
    """
    Zwraca odpowiednią strzałkę dla sortowania (↑ lub ↓).
    - Wskazuje aktualny kierunek sortowania: rosnący (↑) lub malejący (↓).
    """
    if current_sort == column:
        return '↑' if current_order == 'asc' else '↓'
    # Domyślnie brak strzałki, gdy kolumna nie jest sortowana
    return ''
