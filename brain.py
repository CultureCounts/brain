import os
import imp
import sys
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

def load_config(configs):
    for f in configs:
        if os.path.isfile(f):
            return imp.load_source("brain.config", f)

def check_match(matchers, entry):
    for m in matchers:
        if all(item in entry.items() for item in m.items()):
            return True

def handle_post(handler):
    handler.send_response(200)
    handler.send_header('Content-type', 'text/plain')
    handler.end_headers()
    data = json.loads(handler.rfile.read(int(handler.headers['Content-Length'])))
    for d in data:
        if check_match(handler.config.MATCHES, d):
            print "MATCH", d.get("time"), d.get("host"), d.get("plugin"), d.get("type"), d.get("type_instance"), d.get("plugin_instance"), d.get("dsnames"), d.get("values")
    handler.wfile.write("true")

def run_server(config):
    class handler(BaseHTTPRequestHandler):
        config=config
        do_POST = handle_post
    httpd = HTTPServer(('', 8555), handler)
    print 'Starting brain httpd server...'
    httpd.serve_forever()

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

