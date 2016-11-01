from functools import partial
from checks import check_exceed

MATCHES = [
    {"plugin": "df", "type": "df_complex", "type_instance": "free", "plugin_instance": "root"},
    {"plugin": "memory", "type_instance": "free"},
    {"plugin": "load", "check": partial(check_exceed, 0.1)},
    {"plugin": "swap", "type_instance": "free"},
]

SERVER_TIMEOUT = 30

ALERT = "echo"
