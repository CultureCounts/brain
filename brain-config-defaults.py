MATCHES = [
    {"plugin": "df", "type": "df_complex", "type_instance": "free", "plugin_instance": "root"},
    {"plugin": "memory", "type_instance": "free"},
    {"plugin": "load", "check": lambda d: d.get("values", [0, 0, 0])[0] > 0.1 and "CPU load is high (%.2f)" % d.get("values")[0]},
    {"plugin": "swap", "type_instance": "free"},
]

SERVER_TIMEOUT = 30

ALERT = "echo"
