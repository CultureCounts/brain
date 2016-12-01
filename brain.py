#!/usr/bin/env python

import os
import imp
import sys
import json
import time
import signal
from functools import partial
from random import random
from datetime import datetime
from subprocess import call, Popen, PIPE
from Queue import Queue, Empty
from threading import Thread, Event
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

# unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

def load_config(configs):
    for f in configs:
        if os.path.isfile(f):
            return imp.load_source("config", f)

def merge_config(config, d):
    return dict(config.SERVERS.get("default", {}), **config.SERVERS.get(d.get("host", None), {}))

def get_match(config, entry):
    matchers = merge_config(config, entry).get("matchers", [])
    for m in matchers:
        if all(item in entry.items() for item in m.items() if item[0] != "check"):
            return m

def update_hysteresis(hysteresis_states, host, match, d):
    state = hysteresis_states.get(host, {})
    check = match.get("check", lambda x: None)(d)
    key = tuple(sorted([m for m in match.items() if m[0] != "check"]))
    #print host, key, check
    if check and not (state.has_key(key) and state[key]):
        state[key] = check
        return check
    state[key] = check

def check_host_pings(host):
    return call("ping %s -c 1" % host,
            stderr=PIPE,
            stdout=PIPE,
            shell=True) == 0

def get_date():
    return datetime.now().strftime("%Y-%m-%d %X")

def handle_log(handler, *args, **kwargs):
    pass

def handle_post(handler):
    handler.send_response(200)
    handler.send_header('Content-type', 'text/plain')
    handler.end_headers()
    data = json.loads(handler.rfile.read(int(handler.headers['Content-Length'])))
    for d in data:
        match = get_match(handler.config, d)
        if match:
            handler.q.put(["MATCH", d])
        else:
            handler.q.put(["PING", {"host": d.get("host")}])
    handler.wfile.write("true")

def handle_alert(alert, server, message):
    date = get_date()
    print date, "Alert:", server, message
    call('%s "%s %s %s"' % (alert, date, server, message), shell=True)

def handle_queue(q, config, exit):
    last_contact = {}
    hysteresis_state = {}
    last_online = None
    while not exit.isSet():
        now = time.time()
        try:
            t, d = q.get(True, 1)
        except Empty:
            t, d = [None, None]
        # log time from this host
        if d and d.get("host", None):
            host = d.get("host", None)
            if not last_contact.has_key(d.get("host")):
                print get_date(), "Connected:", d.get("host")
            last_contact[host] = now
            if not hysteresis_state.has_key(host):
                hysteresis_state[host] = {}
        merged_config = merge_config(config, d or {})
        command = merged_config.get("command", "")
        timeout = merged_config.get("timeout", 120)
        #print d, command, timeout
        if t == "MATCH" and d and d.get("host", None):
            match = get_match(config, d)
            host = d.get("host")
            result = update_hysteresis(hysteresis_state, host, match, d)
            if "--raw" in sys.argv:
                print "MATCH", d, match
                print "TEST", result
                print
            if result and command:
                handle_alert(command, host, result)
        # make sure we are connected
        if not last_online or last_online < now - timeout / 2:
            for s in config.KNOWN_GOOD_HOSTS:
                if check_host_pings(s):
                    if not last_online:
                        print get_date(), "Online."
                    last_online = now
        if last_online and last_online > now - timeout:
            # check last_contact for all servers
            for s in last_contact:
                last_state = hysteresis_state[s].get("connection")
                if last_contact[s] < now - timeout:
                    hysteresis_state[s]["connection"] = "No response from server " + s + " for " + str(int(timeout / 60)) + " minutes."
                elif hysteresis_state[s].has_key("connection"):
                    del hysteresis_state[s]["connection"]
                if hysteresis_state[s].get("connection", None) and not last_state:
                    handle_alert(command, s, hysteresis_state[s]["connection"])
        elif last_online:
            print get_date(), "Offline."
            last_online = None
            known_servers = last_contact.keys()
            for s in known_servers:
                del last_contact[s]

def maintain_tunnel(tunnelcommand, server, exit):
    time.sleep(random() * 0.3)
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    while not exit.isSet():
        print get_date(), "Tunnel starting:", tunnelcommand
        p = Popen(tunnelcommand, stderr=sys.stderr, stdout=sys.stdout, shell=True, preexec_fn=os.setsid)
        while not exit.isSet() and not p.poll():
            time.sleep(0.1)
        if exit.isSet():
            os.killpg(p.pid, signal.SIGINT)
        print get_date(), "Tunnel closed:", tunnelcommand
        time.sleep(0.1)
        # lets us ctrl-C out
        for x in range(30):
            if not exit.isSet():
                time.sleep(1)

def handle_exit(exit, httpd, runner, tunnels, signum, frame):
    print get_date(), "Caught exit signal:", signum
    exit.set()
    runner.join()
    [tunnel.join() for tunnel in tunnels]
    httpd.socket.close()
    print get_date(), "Exiting."

def run_server(config):
    queue = Queue()
    exit = Event()
    class handler(BaseHTTPRequestHandler):
        q=queue
        config=config
        do_POST = handle_post
        log_message = handle_log
        contact = []
    httpd = HTTPServer(('', 8555), handler)
    runner = Thread(target=handle_queue, args=(queue,config,exit))
    tunnels = [Thread(target=maintain_tunnel, args=(config.SERVERS[c].get("tunnel"), c, exit)) for c in config.SERVERS if config.SERVERS[c].get("tunnel", None)]
    
    exitfn = partial(handle_exit, exit, httpd, runner, tunnels)
    signal.signal(signal.SIGTERM, exitfn)
    signal.signal(signal.SIGINT, exitfn)
    
    runner.start()
    [tunnel.start() for tunnel in tunnels]
    print get_date(), 'Starting.'
    try:
        httpd.serve_forever()
    except Exception, e:
        if not exit.isSet():
            print get_date(), "httpd:", str(e)

if __name__ == "__main__":
    from sys import argv
    if len(argv) > 1 and not argv[1].startswith("-"):
        if os.path.isfile(argv[1]):
            configs = [argv[1]]
        else:
            sys.stderr.write(argv[1] + " does not exist.\n")
            sys.exit(1)
    else:
        configs = [
            os.path.join(os.environ.get("HOME", "/"), ".brain-config.py"),
            os.path.join(os.path.dirname(__file__), "brain-config-defaults.py")]
    config = load_config(configs)
    run_server(config)

