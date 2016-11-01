def check_exceed(val, d):
    load = d.get("values", [0, 0, 0])[0]
    if load > val:
        return "Load is high: " + str(load)

