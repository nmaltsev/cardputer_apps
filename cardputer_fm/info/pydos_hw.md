Pydos_hw exposes:
```Python
Pydos_hw.CS   # list of chip select pins
Pydos_hw.SPI  # function to get SPI per slot
```
So the number of usable slots is:
```Python
len(Pydos_hw.CS)
```
(while skipping None entries)
