import os
import imp
import sys
import json
import time
from datetime import datetime
from subprocess import call, PIPE
from Queue import Queue, Empty
from threading import Thread
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

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

def update_hysteresis(state, match, d):
    check = match.get("check", lambda x: None)(d)
    key = tuple(sorted([m for m in match.items() if m[0] != "check"]))
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
    print "Alert:", date, server, message
    call('%s "%s %s %s"' % (alert, date, server, message), shell=True)

def handle_queue(q, config):
    last_contact = {}
    hysteresis_state = {}
    last_online = None
    run = True
    while run:
        try:
            now = time.time()
            try:
                t, d = q.get(True, 1)
            except Empty:
                t, d = [None, None]
            # log time from this host
            if d and d.get("host", None):
                host = d.get("host", None)
                if not last_contact.has_key(d.get("host")):
                    print "Connected:", get_date(), d.get("host")
                last_contact[d.get("host")] = now
            merged_config = merge_config(config, d or {})
            command = merged_config.get("command", "")
            timeout = merged_config.get("timeout", 120)
            #print d, command, timeout
            if t == "EXIT":
                run = False
            elif t == "MATCH" and d:
                match = get_match(config, d)
                #print
                #print "MATCH", d, match
                result = update_hysteresis(hysteresis_state, match, d)
                #print "TEST", result
                if result and command:
                    handle_alert(command, s, result)
            # make sure we are connected
            if not last_online or last_online < now - timeout / 2:
                for s in config.KNOWN_GOOD_HOSTS:
                    if check_host_pings(s):
                        if not last_online:
                            print "Online:", get_date()
                        last_online = now
            if last_online and last_online > now - timeout:
                # check last_contact for all servers
                for s in last_contact:
                    last_state = hysteresis_state.get(s, None)
                    if last_contact[s] < now - timeout:
                        hysteresis_state[s] = "No response from server " + s + " for " + str(int(timeout / 60)) + " minutes."
                    else:
                        hysteresis_state[s] = None
                    if hysteresis_state[s] and not last_state:
                        handle_alert(command, s, hysteresis_state[s])
            elif last_online:
                print "Offline:", get_date()
                last_online = None
                known_servers = last_contact.keys()
                for s in known_servers:
                    del hysteresis_state[s]
                    del last_contact[s]
        except KeyboardInterrupt:
            run = False

def run_server(config):
    queue = Queue()
    class handler(BaseHTTPRequestHandler):
        q=queue
        config=config
        do_POST = handle_post
        log_message = handle_log
        contact = []
    httpd = HTTPServer(('', 8555), handler)
    t = Thread(target=handle_queue, args=(queue,config,))
    try:
        t.start()
        print 'Starting brain httpd server...'
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "Exiting."
        httpd.socket.close()
        queue.put(["EXIT", None])
        t.join()

if __name__ == "__main__":
    from sys import argv
    if len(argv) > 1:
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

