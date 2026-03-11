from datetime import datetime, timedelta, date
from typing import List


def get_commission_weeks_for_month(year: int, month: int) -> List[List[date]]:
    """
    Genera semanas para cálculo de comisiones según reglas de negocio:

    1. Semana 1:
       - Si 1ro es Dom, Lun o Mar → Días 1 al 8
       - Si 1ro es Mié, Jue, Vie o Sáb → Días 1 hasta el próximo Domingo
    2. Semanas 2+: Bloques de 7 días (Lunes a Domingo)
    3. Última semana:
       - Si tiene < 5 días → se fusiona con la semana anterior
       - Si tiene >= 5 días → se queda como está
    4. Solo días del mes actual

    Args:
        year (int): Año
        month (int): Mes (1-12)

    Returns:
        List[List[date]]: Lista de semanas
    """
    # 1. Obtener último día del mes
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)

    last_day_of_month = (next_month_first - timedelta(days=1)).day
    first_day = date(year, month, 1)

    weeks = []

    # 2. Generar Semana 1
    week_1 = []
    weekday_of_first = first_day.weekday()  # 0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie, 5=Sab, 6=Dom

    # Si es Miércoles(2), Jueves(3), Viernes(4) o Sábado(5) → hasta el próximo Domingo
    if weekday_of_first in [2, 3, 4, 5]:
        days_until_sunday = 6 - weekday_of_first
        end_day_week1 = 1 + days_until_sunday
    else:
        # Domingo(6), Lunes(0) o Martes(1) → días 1 al 8
        end_day_week1 = 8

    # Asegurar no pasar del último día del mes
    end_day_week1 = min(end_day_week1, last_day_of_month)

    for day in range(1, end_day_week1 + 1):
        week_1.append(date(year, month, day))
    weeks.append(week_1)

    # 3. Generar Semanas 2+ (bloques de 7 días)
    current_day = end_day_week1 + 1

    while current_day <= last_day_of_month:
        week_days = []

        # Agregar hasta 7 días o hasta fin de mes
        for i in range(7):
            day_num = current_day + i
            if day_num > last_day_of_month:
                break
            week_days.append(date(year, month, day_num))

        if week_days:
            weeks.append(week_days)
            current_day += len(week_days)
        else:
            break

    # 4. Aplicar regla de fusión: si última semana < 5 días, fusionar con la anterior
    if len(weeks) > 1 and len(weeks[-1]) < 4:
        last_week = weeks.pop()  # Remover última semana
        weeks[-1].extend(last_week)  # Fusionar con la semana anterior

    return weeks


# --- Ejemplo de Uso ---
if __name__ == "__main__":
    test_cases = [
        (2026, 2, "Febrero 2026 (28 días) - 01/02 = Domingo"),
        (2026, 3, "Marzo 2026 (31 días) - 01/03 = Domingo"),
        (2026, 4, "Abril 2026 (30 días) - 01/04 = Miércoles"),
    ]

    for year, month, description in test_cases:
        print("=" * 70)
        print(description)
        print("=" * 70)
        semanas = get_commission_weeks_for_month(year, month)
        for i, semana in enumerate(semanas, 1):
            dias_str = ", ".join([f"{d.day:02d}/{d.month:02d}" for d in semana])
            print(f"Semana {i}: {dias_str} ({len(semana)} días)")
        print()