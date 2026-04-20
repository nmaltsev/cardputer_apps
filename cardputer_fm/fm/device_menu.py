try:
    import board
    HAS_BOARD = True
except ImportError:
    HAS_BOARD = False

import os
import time


from .utils import pad_line, get_key
from .utils_date_sync import wifi_get_and_print_datetime 
from .utils_date import prompt_and_set_date
from .sdcard_cp import SDCard


# TODO rename in settings menu


# ---------- BRIGHTNESS ----------
def brght(level=None):
    if not HAS_BOARD:
        return None

    if level is None:
        return board.DISPLAY.brightness
    else:
        try:
            level = float(level)
            if not (0.0 <= level <= 1.0):
                level = 0.35
        except (ValueError, TypeError):
            level = 0.35

        board.DISPLAY.brightness = level
        return level


# ---------- SD HELPERS ----------
def ensure_dir(path):
    try:
        os.mkdir(path)
    except:
        pass


def mount_sd1(slot, mount_point):
    # TODO old stable solution
    if not HAS_BOARD:
        print("SD not available on this platform")
        return

    try:
        import storage
        from pydos_hw import Pydos_hw

        # fallback like original PyDOS
        try:
            import adafruit_sdcard
        except ImportError:
            import sdcardio as adafruit_sdcard

        ensure_dir("/sd")
        ensure_dir(mount_point)

        spi = Pydos_hw.SPI(slot - 1)

        if spi is None:
            print("SPI not available for slot", slot)
            return

        cs = Pydos_hw.CS[slot - 1]

        if cs is None:
            print("CS pin not defined for slot", slot)
            return

        # ---- create SD ----
        sd = adafruit_sdcard.SDCard(spi, cs)
        vfs = storage.VfsFat(sd)

        storage.mount(vfs, mount_point)

        print("mounted:", mount_point)

    except Exception as e:
        print("mount error:", e)

def mount_sd(slot, mount_point):
    try:
        import storage
        import digitalio
        from pydos_hw import Pydos_hw

        # normalize path
        mount_point = mount_point.strip().strip('"').strip("'")

        # prevent double mount
        try:
            for m in storage.getmounts():
                if m.mount_point == mount_point:
                    print("already mounted:", mount_point)
                    return
        except:
            pass

        ensure_dir("/sd")
        ensure_dir(mount_point)

        spi = Pydos_hw.SPI(slot - 1)
        cs_pin = Pydos_hw.CS[slot - 1]

        cs = digitalio.DigitalInOut(cs_pin)

        sd = SDCard(spi, cs)
        vfs = storage.VfsFat(sd)

        storage.mount(vfs, mount_point)

        print("mounted:", mount_point)

    except Exception as e:
        print("mount error:", e)

def unmount_sd(path):
    if not HAS_BOARD:
        print("SD not available on this platform")
        return
    try:
        import storage
        storage.umount(path)
        print("unmounted:", path)
    except Exception as e:
        print("unmount error:", e)

# ---------- DEVICE MENU ----------
def device_menu():
    while True:
        print()
        if not HAS_BOARD:
            print("No device features available")
            print(pad_line("> q"))
            key = get_key()
            if key == 'q':
                break
            continue
        print("1 mount sd cards")
        print("2 unmount sd cards")
        print("3 adjust brightness")
        print("4 set date; 5 sync date")


        print(pad_line("> 1-3 q"))

        key = get_key()

        if key == 'q':
            break

        # ---------- MOUNT ----------
        elif key == '1':
            print("Mount SD:")
            #  TOOD get number of slots
            print("1 -> /sd/sd1")
            print("2 -> /sd/sd2")

            k = get_key()

            if k == '1':
                mount_sd(1, "/sd/sd1")
            elif k == '2':
                mount_sd(2, "/sd/sd2")
            elif k == '3':
                mount_sd1(1, "/sd/sd1")

        # ---------- UNMOUNT ----------
        elif key == '2':
            print("Unmount:")
            print("0 -> ALL")
            print("1 -> /sd/sd1")
            print("2 -> /sd/sd2")

            k = get_key()

            if k == '0':
                unmount_sd("/sd/sd1")
                unmount_sd("/sd/sd2")
            elif k == '1':
                unmount_sd("/sd/sd1")
            elif k == '2':
                unmount_sd("/sd/sd2")

        # ---------- BRIGHTNESS ----------
        elif key == '3':
            current = brght()
            print("current:", current)

            level = input("enter brightness % (10-100): ").strip()

            try:
                level = float(level) / 100.0
                new = brght(level)
                print("brightness set:", new)
            except:
                print("invalid value")

        elif key == '4':
            prompt_and_set_date()

        elif key == '5':
            wifi_get_and_print_datetime(tz_offset=2)  # e.g. France (UTC+2 DST)
