import time
import board
import analogio
import displayio
import terminalio
# from adafruit_display_text import label

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

# title = label.Label(
#     terminalio.FONT, text="Cardputer Battery", color=0xFFFFFF, x=20, y=20
# )
# voltage_label = label.Label(
#     terminalio.FONT, text="Voltage: --.-- V", color=0x00FF00, x=20, y=60
# )
# status_label = label.Label(
#     terminalio.FONT, text="Status: --", color=0xFFFF00, x=20, y=90
# )

# main_group.append(title)
# main_group.append(voltage_label)
# main_group.append(status_label)

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
    
    # voltage_label.text = f"Voltage: {vbat:.3f} V"
    # status_label.text = f"Status: {status}"
    # status_label.color = color
    print(f"Voltage: {vbat:.3f} V")
    print(f"Status: {status}")
    
    print(f"Battery: {vbat:.3f} V  |  {status}")
    
    time.sleep(2.0)   # Update every 2 seconds