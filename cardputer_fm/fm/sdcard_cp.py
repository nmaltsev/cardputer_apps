import time
import digitalio
import os

_CMD_TIMEOUT = 100

_R1_IDLE_STATE = 1 << 0
_R1_ILLEGAL_COMMAND = 1 << 2

_TOKEN_CMD25 = 0xFC
_TOKEN_STOP_TRAN = 0xFD
_TOKEN_DATA = 0xFE


# ---------- DEBUG CONFIG ----------
SD_DEBUG = True
SD_DEBUG_FILE = "/sd/sd_debug.log"


class SDCard:
    def __init__(self, spi, cs, baudrate=1320000):
        self.spi = spi
        self.cs = cs

        # ---- LOCK SPI ONCE ----
        while not self.spi.try_lock():
            pass

        # slow init speed
        self.spi.configure(baudrate=100000, phase=0, polarity=0)

        self.cmdbuf = bytearray(6)
        self.tokenbuf = bytearray(1)
        self.dummybuf = bytearray(512)

        for i in range(512):
            self.dummybuf[i] = 0xFF

        # ensure CS is DigitalInOut
        if not isinstance(self.cs, digitalio.DigitalInOut):
            self.cs = digitalio.DigitalInOut(self.cs)

        self.cs.direction = digitalio.Direction.OUTPUT
        self.cs.value = True

        # small delay for stability
        time.sleep(0.2)

        # wake-up clocks (80+ cycles)
        for _ in range(32):
            self._spi_write(b"\xff")

        self._dbg("---- INIT START ----")

        # init card
        self.init_card(baudrate)

    # ---------- DEBUG ----------
    def _dbg(self, *args):
        if not SD_DEBUG:
            return

        msg = "[SD] " + " ".join(str(a) for a in args)

        # try file logging first
        try:
            with open(SD_DEBUG_FILE, "a") as f:
                f.write(msg + "\n")
        except Exception:
            # fallback to console
            print(msg)

    def _deselect(self):
        self.cs.value = True
        self._spi_write(b"\xff")

    # ---------- SPI helpers ----------
    def _spi_write(self, buf):
        self.spi.write(buf)

    def _spi_readinto(self, buf, write_value=0xFF):
        dummy = bytes([write_value & 0xFF]) * len(buf)
        self.spi.write_readinto(dummy, buf)

    def _spi_read(self, n=1):
        buf = bytearray(n)
        self._spi_readinto(buf)
        return buf

    # ---------- init ----------
    def init_spi(self, baudrate):
        self.spi.configure(baudrate=baudrate, phase=0, polarity=0)

    def init_card(self, baudrate):
        # CMD0: reset
        for _ in range(5):
            r = self.cmd(0, 0, 0x95)
            if r == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card (CMD0 failed)")

        self._dbg("CMD0 success")

        # CMD8: check version
        r = self.cmd(8, 0x01AA, 0x87, 4)
        self._dbg("CMD8 response received")

        if r == _R1_IDLE_STATE:
            self._dbg("Card is v2")
            self.init_card_v2()
        elif r == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            self._dbg("Card is v1")
            self.init_card_v1()
        else:
            raise OSError("cannot determine SD version")

        # CMD9: read CSD
        if self.cmd(9, 0, 0, 0, False) != 0:
            raise OSError("no response from SD")

        csd = bytearray(16)
        self.readinto(csd)

        if csd[0] & 0xC0 == 0x40:
            self.sectors = ((csd[8] << 8 | csd[9]) + 1) * 1024
        elif csd[0] & 0xC0 == 0x00:
            c_size = (csd[6] & 3) << 10 | csd[7] << 2 | csd[8] >> 6
            c_mult = (csd[9] & 3) << 1 | csd[10] >> 7
            read_bl_len = csd[5] & 0xF
            capacity = (c_size + 1) * (2 ** (c_mult + 2)) * (2 ** read_bl_len)
            self.sectors = capacity // 512
        else:
            raise OSError("unsupported CSD")

        # CMD16: set block size
        if self.cmd(16, 512, 0) != 0:
            raise OSError("set block size failed")

        # switch to fast SPI
        self.init_spi(baudrate)

    def init_card_v1(self):
        for _ in range(_CMD_TIMEOUT):
            time.sleep(0.05)
            self.cmd(55, 0, 0)
            r = self.cmd(41, 0, 0)
            self._dbg(f"ACMD41 (v1) -> 0x{r:02X}")
            if r == 0:
                self.cdv = 512
                return
        raise OSError("timeout waiting for v1 card")

    def init_card_v2(self):
        for _ in range(_CMD_TIMEOUT):
            time.sleep(0.05)

            self.cmd(58, 0, 0, 4)
            self.cmd(55, 0, 0)

            r = self.cmd(41, 0x40000000, 0)
            self._dbg(f"ACMD41 -> 0x{r:02X}")

            if r == 0:
                self.cmd(58, 0, 0, -4)
                ocr = self.tokenbuf[0]
                self.cdv = 1 if (ocr & 0x40) else 512
                return

        raise OSError("timeout waiting for v2 card")

    # ---------- command ----------
    def cmd(self, cmd, arg, crc, final=0, release=True, skip1=False):
        # ensure proper deselect timing
        self.cs.value = True
        self._spi_write(b"\xff")

        self.cs.value = False

        self._dbg(f"CMD{cmd} arg=0x{arg:08X}")

        buf = self.cmdbuf
        buf[0] = 0x40 | cmd
        buf[1] = (arg >> 24) & 0xFF
        buf[2] = (arg >> 16) & 0xFF
        buf[3] = (arg >> 8) & 0xFF
        buf[4] = arg & 0xFF
        buf[5] = crc & 0xFF

        self._spi_write(buf)

        if skip1:
            self._spi_readinto(self.tokenbuf)

        for _ in range(_CMD_TIMEOUT):
            self._spi_readinto(self.tokenbuf)
            r = self.tokenbuf[0]

            if not (r & 0x80):
                self._dbg(f" -> R1=0x{r:02X}")

                extra = []

                if final < 0:
                    self._spi_readinto(self.tokenbuf)
                    extra.append(self.tokenbuf[0])
                    final = -1 - final

                for _ in range(final):
                    b = self._spi_read(1)[0]
                    extra.append(b)

                if extra:
                    self._dbg("   extra:", " ".join(f"{b:02X}" for b in extra))

                if release:
                    self._deselect()

                return r

        self._deselect()
        return -1

    # ---------- read ----------
    def readinto(self, buf):
        self.cs.value = False

        for _ in range(_CMD_TIMEOUT):
            self._spi_readinto(self.tokenbuf)
            if self.tokenbuf[0] == _TOKEN_DATA:
                self._dbg("DATA TOKEN received")
                break
            time.sleep(0.001)
        else:
            self.cs.value = True
            raise OSError("read timeout")

        self._spi_readinto(buf)

        self._spi_write(b"\xff")
        self._spi_write(b"\xff")

        self.cs.value = True
        self._spi_write(b"\xff")

    def readblocks(self, block, buf):
        self._spi_write(b"\xff")

        if self.cmd(17, block * self.cdv, 0, release=False) != 0:
            self.cs.value = True
            raise OSError("read error")

        self.readinto(buf)

    # ---------- write ----------
    def write(self, token, buf):
        self.cs.value = False

        self._spi_write(bytes([token & 0xFF]))
        self._spi_write(buf)
        self._spi_write(b"\xff\xff")

        if (self._spi_read(1)[0] & 0x1F) != 0x05:
            self.cs.value = True
            return

        while self._spi_read(1)[0] == 0:
            pass

        self.cs.value = True
        self._spi_write(b"\xff")

    def writeblocks(self, block, buf):
        self._spi_write(b"\xff")

        if self.cmd(24, block * self.cdv, 0) != 0:
            raise OSError("write error")

        self.write(_TOKEN_DATA, buf)

    # ---------- ioctl ----------
    def ioctl(self, op, arg):
        if op == 4:
            return self.sectors
        if op == 5:
            return 512
