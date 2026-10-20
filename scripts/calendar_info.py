"""Print the Gregorian/Hijri date and Islamic occasions for the next N days.
Used by the planner to choose themes.

    python scripts/calendar_info.py 7
"""
import datetime as dt
import json
import sys

from hijridate import Gregorian

# (hijri month, day range) -> occasion. Dates are civil-calendar estimates; the
# actual start of a month depends on moon sighting and can differ by a day.
OCCASIONS = [
    (1, range(1, 2), "Islamic New Year (1 Muharram)"),
    (1, range(9, 11), "Day of Ashura (9-10 Muharram)"),
    (9, range(1, 31), "Ramadan"),
    (9, range(21, 30), "Last ten nights of Ramadan (Laylat al-Qadr)"),
    (10, range(1, 4), "Eid al-Fitr"),
    (10, range(4, 30), "Six days of Shawwal fasting"),
    (12, range(1, 10), "First ten days of Dhul Hijjah"),
    (12, range(9, 10), "Day of Arafah"),
    (12, range(10, 14), "Eid al-Adha / Days of Tashreeq"),
]


def info(day):
    h = Gregorian(day.year, day.month, day.day).to_hijri()
    tags = [name for m, days, name in OCCASIONS if h.month == m and h.day in days]
    if day.weekday() == 4:
        tags.append("Friday (Jumu'ah)")
    if day.weekday() in (0, 3):
        tags.append("Sunnah fast day (Monday/Thursday)")
    if h.day in (13, 14, 15):
        tags.append("White days (13-15) sunnah fast")
    return {
        "date": day.isoformat(),
        "weekday": day.strftime("%A"),
        "hijri": f"{h.day} {h.month_name()} {h.year} AH",
        "occasions": tags,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    today = dt.date.today()
    for i in range(n):
        print(json.dumps(info(today + dt.timedelta(days=i)), ensure_ascii=False))
