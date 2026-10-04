#!/usr/bin/env python3
import datetime as dt
import json
import platform
from decimal import Decimal


instant = dt.datetime(2026, 10, 2, 9, 0, tzinfo=dt.timezone.utc)
try:
    json.dumps(Decimal("10.50"))
    decimal_default = "accepted"
except TypeError:
    decimal_default = "TypeError"

print(json.dumps({
    "stack": "Python",
    "runtime": platform.python_version(),
    "library": "stdlib json/datetime",
    "options": "json.dumps defaults; datetime.isoformat()",
    "observed": {
        "datetime": instant.isoformat(),
        "decimalDefault": decimal_default,
        "nullKept": json.loads(json.dumps({"note": None})),
    },
}, sort_keys=True))
