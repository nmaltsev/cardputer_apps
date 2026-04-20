import time

# WiFi + NTP (same approach as getdate.py)

try:
    import adafruit_ntp
    HAS_NTP = True
except:
    HAS_NTP = False

try:
    from pydos_wifi import Pydos_wifi
    from rtc import RTC
    HAS_RTC = True
except:
    HAS_RTC = False


def format_datetime(dt):
    """Format struct_time to YYYY/MM/DD HH:MM:SS"""
    return "{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
        dt.tm_year, dt.tm_mon, dt.tm_mday,
        dt.tm_hour, dt.tm_min, dt.tm_sec
    )


def wifi_get_and_print_datetime(tz_offset=0):
    """
    Connects to WiFi, gets current datetime,
    sets RTC, and prints it.
    """

    # --- Connect WiFi ---
    ssid = Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID')
    password = Pydos_wifi.getenv('CIRCUITPY_WIFI_PASSWORD')

    if ssid is None:
        print("WiFi credentials missing in settings.toml")
        return False

    if not Pydos_wifi.connect(ssid, password):
        print("WiFi connection failed")
        return False

    print("Connected to WiFi")

    # --- Get time via NTP ---
    rtc_clock = rtc.RTC()
    success = False

    try:
        if HAS_NTP:
            ntp = adafruit_ntp.NTP(
                Pydos_wifi._pool,
                server="pool.ntp.org",
                tz_offset=tz_offset
            )

            for _ in range(5):
                try:
                    rtc_clock.datetime = ntp.datetime
                    success = True
                    break
                except:
                    time.sleep(1)

        # fallback using radio.get_time()
        if not success:
            for _ in range(5):
                try:
                    t = Pydos_wifi.radio.get_time()[0]
                    rtc_clock.datetime = time.localtime(t + tz_offset * 3600)
                    success = True
                    break
                except:
                    time.sleep(1)

    except Exception as e:
        print("Time fetch error:", e)

    if not success:
        print("Failed to get time")
        Pydos_wifi.close()
        return False

    # --- Read & print datetime ---
    current = rtc_clock.datetime
    print("Current DateTime:", format_datetime(current))

    # --- Cleanup ---
    Pydos_wifi.close()

    return True