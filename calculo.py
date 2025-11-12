from datetime import datetime, timedelta


def get_weeks_for_month(year, month):
    # Fecha de inicio del mes
    start_date = datetime(year, month, 1)

    # Fecha final del mes
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    weeks = []
    current_date = start_date

    while current_date <= end_date:
        days_in_week = []
        temp_date = current_date

        # Agregar días hasta el domingo o hasta el final del mes
        while temp_date.weekday() < 6 and temp_date <= end_date:
            days_in_week.append(temp_date.date())
            temp_date += timedelta(days=1)

        # Si el día actual era un domingo, también lo agregamos
        if temp_date.weekday() == 6 and temp_date <= end_date:
            days_in_week.append(temp_date.date())
            temp_date += timedelta(days=1)

        # Si la semana tiene menos de 4 días, fusionar con la siguiente semana (hasta el próximo domingo)
        if len(days_in_week) < 4:
            # Continuar agregando días hasta el próximo domingo
            while temp_date.weekday() != 6 and temp_date <= end_date:
                days_in_week.append(temp_date.date())
                temp_date += timedelta(days=1)
            if temp_date <= end_date:
                days_in_week.append(temp_date.date())
                temp_date += timedelta(days=1)

        weeks.append(days_in_week)
        current_date = temp_date

    return weeks


def print_weeks(weeks, month, year):
    print(f"\nSemanas para {month}/{year}:")
    for i, week in enumerate(weeks):
        start_day = week[0]
        end_day = week[-1]
        num_days = len(week)
        print(f"Semana {i + 1}: {start_day} a {end_day} ({num_days} días)")
    print("\n")


# Ejemplo de uso:
if __name__ == "__main__":
    # Cambia el año y mes que quieras calcular
    year = 2025
    month = 10  # Noviembre 2025

    weeks = get_weeks_for_month(year, month)
    print_weeks(weeks, month, year)