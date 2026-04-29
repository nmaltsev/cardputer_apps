try:
    import board
    HAS_BOARD = True
except ImportError:
    HAS_BOARD = False

import os
import time

from .utils import pad_line, get_key, open_settings
from .utils_date_sync import wifi_get_and_print_datetime 
from .utils_date import prompt_and_set_date
# from .sdcard_cp import SDCard
from .sdcard_cp1 import SDCard
#from .sdcard_cp2 import SDCard


# TODO rename in settings menu

def save_board_pins(filepath):
    import board
    import supervisor

    try:
        items = dir(board)
        superviser_runtime_items = dir(supervisor.runtime)

        with open(filepath, "w") as f:
            f.write('board module exports:\n')
            for item in items:
                f.write(item + "\n")
            f.write('supervisor.runtime module exports:\n')
            for item in superviser_runtime_items:
                f.write(item + "\n")

        print("Saved board pins to:", filepath)

    except Exception as e:
        print("Error saving board pins:", e)

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
    if not HAS_BOARD:
        print("SD not available on this platform")
        return

    try:
        import storage
        import digitalio
        from pydos_hw import Pydos_hw
    except ImportError:
        print("SD not available: missing modules")
        return

    # normalize path
    mount_point = mount_point.strip()

    try:
        for m in storage.getmounts():
            if m.mount_point.rstrip("/") == mount_point.rstrip("/"):
                print("already mounted:", mount_point)
                return
    except:
        pass

    ensure_dir("/sd")
    ensure_dir(mount_point)

    spi = None
    cs = None
    mounted = False

    try:
        spi = Pydos_hw.SPI(slot - 1)
        if spi is None:
            print("SPI not available for slot", slot)
            return

        cs_pin = Pydos_hw.CS[slot - 1]
        if cs_pin is None:
            print("CS pin not defined for slot", slot)
            return

        cs = digitalio.DigitalInOut(cs_pin)

        sd = SDCard(spi, cs)
        vfs = storage.VfsFat(sd)

        storage.mount(vfs, mount_point)
        print("mounted:", mount_point)
        mounted = True

    except Exception as e:
        err_str = str(e).lower()
        if "no sd card" in err_str or "cmd0 failed" in err_str:
            print(f"No SD card detected in slot {slot} - insert a card and try again")
        else:
            print("mount error:", e)
        
        try:
            if cs:
                cs.deinit()
        except:
            pass

        try:
            if spi:
                spi.unlock()
        except:
            pass


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

# ---------- SD SLOT DETECTION ----------
def get_sd_slots():
    try:
        from pydos_hw import Pydos_hw

        slots = []
        for i, cs in enumerate(Pydos_hw.CS):
            if cs is not None and Pydos_hw.SPI(i) is not None:
                slots.append(i + 1)  # slots are 1-based

        return slots

    except Exception as e:
        print("slot detect error:", e)
        return []

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
        print("4 set date; 5 sync date; 7 open settings")


        print(pad_line("> 1-3 q"))

        key = get_key()

        if key == 'q':
            break

        # ---------- MOUNT ----------
        elif key == '1':
            print("Mount SD:")

            slots = get_sd_slots()

            if not slots:
                print("No SD slots available")
                continue

            # show dynamic menu
            for s in slots:
                print(f"{s} -> /sd/sd{s}")

            print("Select slot:")
            k = input().strip()

            if k == '0':
                mount_sd1(1, "/sd/sd1")
                continue

            try:
                slot = int(k)
            except:
                print("invalid selection (enter a number)")
                continue

            if slot in slots:
                mount_sd(slot, f"/sd/sd{slot}")
            else:
                print("invalid slot")
        # ---------- UNMOUNT ----------
        elif key == '2':
            print("Unmount:")
            print("0 -> ALL")
            i = 0
            for m in storage.getmounts():
                print(i+1, ' -> ', m.mount_point)

            k = get_key()
            try:
                slot = int(k)
            except:
                print("invalid selection (enter a number)")
                continue

            if k == 0:
                for m in storage.getmounts():
                    storage.unmount(m.mount_point)
            else :
                mounts = storage.getmounts()
                if k > -1 and k < len(mounts):
                    storage.unmount(mounts[k].mount_point)


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
        
        elif key == '6':
            # import supervisor
            # print(supervisor.runtime.display.height)
            # print('Dispaly: ', supervisor.runtime.display)
            save_board_pins('/usr/board_pins.txt')

        elif key == '7':
            open_settings()
