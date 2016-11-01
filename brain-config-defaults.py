# Which collectd messages we care about.
# Each incoming collectd message will be compared against each of these dictionaries.
# If all keys from a dictionary listed below matches against a key in the collectd message we have a match.
# The "check" key contains a function that is run to determine the alert (if any) that should be raised.
MATCHES = [
    {"plugin": "df", "type": "df_complex", "type_instance": "free", "plugin_instance": "root", "check": lambda d: d.get("values", [0])[0] / float(1<<30) < 1.0 and "Disk space is low (%dmb)" % (d.get("values", [0])[0] / float(1<<30))},
    #{"plugin": "memory", "type_instance": "free", "check": printfn},
    {"plugin": "load", "check": lambda d: d.get("values", [0, 0, 0])[0] > 2.0 and "CPU load is high (%.2f)" % d.get("values")[0]},
    {"plugin": "swap", "type_instance": "free", "check": lambda d: d.get("values", [0])[0] / float(1<<20) < 100 and "Swap/memory is low (%dmb)" % (d.get("values", [0])[0] / float(1<<20))},
]

# Hosts to ping to determine if we are online or not
# If all fail we are considered to be offline
KNOWN_GOOD_HOSTS = ["8.8.8.8", "198.35.26.96"]

# How long to wait before we consider a host non-responsive
SERVER_TIMEOUT = 120

# Shell command that should be run when an alert comes in
# Single argument passed - the alert message
ALERT = "echo"
