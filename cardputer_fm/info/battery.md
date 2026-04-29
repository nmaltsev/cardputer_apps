Here's a **CircuitPython** script for the **M5Stack Cardputer** that displays the current **battery voltage** and an estimated **charging status**.

### Important Notes for Cardputer
- The Cardputer **does not have a reliable direct "isCharging" flag** like some other M5Stack devices (e.g., CoreS3 with AXP2101). The official Arduino library even states that charging status and current cannot be read due to hardware limitations.
- The best proxy is to **monitor the battery voltage** on **GPIO10** (connected to the battery ADC).
  - When **charging** (and the power switch is ON), voltage is usually **~4.1V – 4.2V**.
  - When **not charging** (on battery), it typically ranges from ~3.7V (full) down to ~3.3V (low).

```python
# code.py - Battery status for M5Stack Cardputer (CircuitPython)
import time
import board
import analogio
import displayio
import terminalio
from adafruit_display_text import label

# Initialize the display (Cardputer uses ST7789 240x135)
displayio.release_displays()

spi = board.SPI()
tft_cs = board.LCD_CS
tft_dc = board.LCD_DC
tft_rst = board.LCD_RST

display_bus = displayio.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst
)

display = displayio.OnScreen(
    display_bus,
    width=240,
    height=135,
    rotation=0,           # or 90/180/270 depending on your preference
    auto_refresh=True,
)

# Create text labels
main_group = displayio.Group()
display.root_group = main_group

title = label.Label(
    terminalio.FONT, text="Cardputer Battery", color=0xFFFFFF, x=20, y=20
)
voltage_label = label.Label(
    terminalio.FONT, text="Voltage: --.-- V", color=0x00FF00, x=20, y=60
)
status_label = label.Label(
    terminalio.FONT, text="Status: --", color=0xFFFF00, x=20, y=90
)

main_group.append(title)
main_group.append(voltage_label)
main_group.append(status_label)

# Battery voltage on GPIO10 (ADC)
bat_pin = analogio.AnalogIn(board.G10)

def get_battery_voltage():
    # Raw ADC reading (0-65535)
    raw = bat_pin.value
    
    # Typical voltage divider on Cardputer: battery voltage → ~1/2 on GPIO10
    # Adjust the multiplier if your readings are off (test with known voltages)
    voltage = (raw / 65535) * 3.3 * 2.0   # ≈ 2x because of divider
    
    # More accurate calibration (common values reported by users)
    # voltage = (raw * 3.3 * 2.05) / 65535   # tweak the 2.05 factor if needed
    
    return voltage

print("Cardputer Battery Monitor started")

while True:
    vbat = get_battery_voltage()
    
    # Simple charging / status estimation
    if vbat >= 4.15:
        status = "Charging (Full)"
        color = 0x00FF00
    elif vbat >= 4.0:
        status = "Charging"
        color = 0x00FFAA
    elif vbat >= 3.7:
        status = "Discharging (Good)"
        color = 0xFFFF00
    elif vbat >= 3.5:
        status = "Discharging (Low)"
        color = 0xFFAA00
    else:
        status = "Discharging (Critical)"
        color = 0xFF0000
    
    voltage_label.text = f"Voltage: {vbat:.3f} V"
    status_label.text = f"Status: {status}"
    status_label.color = color
    
    print(f"Battery: {vbat:.3f} V  |  {status}")
    
    time.sleep(2.0)   # Update every 2 seconds
```

### How to Improve Accuracy
1. Run the script and compare the reported voltage with a multimeter on the battery terminals (if accessible).
2. Adjust the multiplier in `get_battery_voltage()` (e.g., change `2.0` to `2.05` or `2.1`) until it matches reality.

### Optional: Use AXP2101 Library (Experimental)
If your Cardputer uses an AXP2101 PMIC (some revisions or Cardputer-Adv might), you can try installing the `axp2101` library and use:

```python
from axp2101 import AXP2101
pmic = AXP2101(board.I2C())
print(pmic.battery_voltage)
```

However, on the standard Cardputer this is **usually not present** — the battery voltage is read directly via the ADC on **G10**.

Would you like a version that also shows an approximate battery percentage (based on a simple voltage-to-% curve) or one that uses the Cardputer keyboard for input?



Here's an improved **CircuitPython** version for the **M5Stack Cardputer** that now includes an **approximate battery percentage** based on a simple voltage-to-% curve.

```python
# code.py - Cardputer Battery Monitor with Percentage
import time
import board
import analogio
import displayio
import terminalio
from adafruit_display_text import label

# ====================== Display Setup ======================
displayio.release_displays()

spi = board.SPI()
tft_cs = board.LCD_CS
tft_dc = board.LCD_DC
tft_rst = board.LCD_RST

display_bus = displayio.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst
)

display = displayio.OnScreen(
    display_bus,
    width=240,
    height=135,
    rotation=0,          # Change to 90 if you prefer landscape
    auto_refresh=True,
)

# Create display group
main_group = displayio.Group()
display.root_group = main_group

# Labels
title = label.Label(terminalio.FONT, text="Cardputer Battery Status", color=0xFFFFFF, x=20, y=20)
voltage_label = label.Label(terminalio.FONT, text="Voltage: --.-- V", color=0x00FF00, x=20, y=55)
percent_label = label.Label(terminalio.FONT, text="Battery: --- %", color=0xFFFF00, x=20, y=80)
status_label = label.Label(terminalio.FONT, text="Status: ----------", color=0xAAAAFF, x=20, y=105)

main_group.append(title)
main_group.append(voltage_label)
main_group.append(percent_label)
main_group.append(status_label)

# ====================== Battery ADC ======================
bat_pin = analogio.AnalogIn(board.G10)

def get_battery_voltage():
    raw = bat_pin.value
    # Most users find a multiplier around 2.0 ~ 2.1 works well on Cardputer
    voltage = (raw / 65535) * 3.3 * 2.05   # ← You can fine-tune this value
    return voltage

def voltage_to_percent(v):
    """Simple linear approximation for Li-ion battery"""
    if v >= 4.20:
        return 100
    elif v >= 3.70:
        # Linear from 4.20V (100%) to 3.70V (~20%)
        return int(20 + (v - 3.70) * (80 / 0.50))
    elif v >= 3.40:
        # Steeper drop in the lower range
        return int(5 + (v - 3.40) * (15 / 0.30))
    else:
        return 0

print("Cardputer Battery Monitor with Percentage started\n")

while True:
    vbat = get_battery_voltage()
    percent = voltage_to_percent(vbat)

    # Determine status and color
    if vbat >= 4.15:
        status = "Charging - Full"
        color = 0x00FF00
    elif vbat >= 4.00:
        status = "Charging"
        color = 0x00FFAA
    elif vbat >= 3.70:
        status = "Good"
        color = 0xFFFF00
    elif vbat >= 3.50:
        status = "Low"
        color = 0xFFAA00
    else:
        status = "Critical!"
        color = 0xFF0000

    # Update labels
    voltage_label.text = f"Voltage: {vbat:.3f} V"
    percent_label.text = f"Battery: {percent:3d} %"
    status_label.text = f"Status: {status}"
    status_label.color = color

    # Also print to serial (for debugging)
    print(f"{vbat:.3f} V  |  {percent:3d}%  |  {status}")

    time.sleep(2.0)
```

### How to Calibrate
1. Fully charge your Cardputer until the voltage stabilizes (usually around **4.15 – 4.20 V**).
2. If the displayed voltage is too high or too low, adjust the multiplier in this line:

   ```python
   voltage = (raw / 65535) * 3.3 * 2.05   # Try 2.00, 2.08, 2.10, etc.
   ```

3. Let the device run on battery and note the voltage when it starts shutting down (usually ~3.3V – 3.4V).

Would you like me to add a **more accurate non-linear curve** (piecewise with typical Li-ion discharge behavior) or include a **progress bar** on the display?