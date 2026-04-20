import time
from sys import implementation

# CircuitPython RTC
try:
    from rtc import RTC
    HAS_RTC = True
except:
    HAS_RTC = False

# -----------------------------
# Utility Functions
# -----------------------------

def format_date_ymd(t=None):
    """Return date as YYYY/MM/DD string"""
    if t is None:
        t = time.localtime()
    return "{:04d}/{:02d}/{:02d}".format(t[0], t[1], t[2])


def print_current_date():
    """Print current date in YYYY/MM/DD format"""
    print(format_date_ymd())


def is_valid_date(year, month, day):
    """Basic date validation (includes leap year logic)"""
    if year < 2000 or year > 2099:
        return False

    if month < 1 or month > 12:
        return False

    mdays = [31, 29 if is_leap_year(year) else 28,
             31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    if day < 1 or day > mdays[month - 1]:
        return False

    return True


def is_leap_year(year):
    """Check leap year"""
    return (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))


# -----------------------------
# RTC Setter
# -----------------------------

def set_rtc_date(year, month, day):
    """Set RTC date (keeps current time)"""
    if not HAS_RTC:
        print("RTC not available")
        return False

    rtc = RTC()
    now = rtc.datetime

    rtc.datetime = time.struct_time((
        year, month, day,
        now.tm_hour,
        now.tm_min,
        now.tm_sec,
        now.tm_wday,
        -1,
        -1
    ))

    return True


# -----------------------------
# Main User Function
# -----------------------------

def prompt_and_set_date():
    """
    1. Prints current date
    2. Prompts user for YYYY, MM, DD
    3. If any input empty → do nothing
    4. Sets RTC date if valid
    """

    print("Current date:", format_date_ymd())

    try:
        year_input = input("Enter year (YYYY): ").strip()
        month_input = input("Enter month (1-12): ").strip()
        day_input = input("Enter day (1-31): ").strip()
    except:
        print("Input error")
        return

    # Requirement: do nothing if ANY input is empty
    if not year_input or not month_input or not day_input:
        print("No changes made.")
        return

    try:
        year = int(year_input)
        month = int(month_input)
        day = int(day_input)
    except:
        print("Invalid numeric input")
        return

    if not is_valid_date(year, month, day):
        print("Invalid date")
        return

    if set_rtc_date(year, month, day):
        print("Date updated to:", format_date_ymd())
    else:
        print("Failed to set date")