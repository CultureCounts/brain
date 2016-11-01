import os
import imp
import sys
import json
import time
from datetime import datetime
from subprocess import call
from Queue import Queue, Empty
from threading import Thread
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

def load_config(configs):
    for f in configs:
        if os.path.isfile(f):
            return imp.load_source("config", f)

def get_match(matchers, entry):
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
        match = get_match(handler.config.MATCHES, d)
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
    run = True
    while run:
        try:
            try:
                t, d = q.get(True, 1)
            except Empty:
                t, d = [None, None]
            # log time from this host
            if d and d.get("host", None):
                host = d.get("host", None)
                if not last_contact.has_key(d.get("host")):
                    print "Connected:", get_date(), d.get("host")
                last_contact[d.get("host")] = time.time()
            if t == "EXIT":
                run = False
            elif t == "MATCH" and d:
                match = get_match(config.MATCHES, d)
                #print
                #print "MATCH", d, match
                result = update_hysteresis(hysteresis_state, match, d)
                #print "TEST", result
                if result:
                    handle_alert(config.ALERT, s, result)
            # check last_contact for all servers
            for s in last_contact:
                last_state = hysteresis_state.get(s, None)
                if last_contact[s] < time.time() - config.SERVER_TIMEOUT:
                    hysteresis_state[s] = "No response from server " + s + " for " + str(int(config.SERVER_TIMEOUT / 60)) + " minutes."
                else:
                    hysteresis_state[s] = None
                if hysteresis_state[s] and not last_state:
                    handle_alert(config.ALERT, s, hysteresis_state[s])
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

