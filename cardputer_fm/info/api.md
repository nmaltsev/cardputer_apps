
## To restart device:
```Python
import microcontroller
microcontroller.reset()
```

## Get current time
```Python
import time
print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
```