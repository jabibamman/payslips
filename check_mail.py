import sys
import time

from mailcode import get_code

timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 120
print("en attente d'un code MyPeopleDoc non lu...")
print("code:", get_code(time.time() - 600, timeout=timeout))
