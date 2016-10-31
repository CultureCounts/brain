import os
import imp
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

def handle_post(handler):
    handler.send_response(200)
    handler.send_header('Content-type', 'text/plain')
    handler.end_headers()
    data = json.loads(handler.rfile.read(int(handler.headers['Content-Length'])))
    for d in data:
        print d.get("time"), d.get("host"), d.get("plugin"), d.get("type"), d.get("type_instance"), d.get("plugin_instance"), d.get("dsnames"), d.get("values")
        #pprint(d)
    handler.wfile.write("true")

class handler(BaseHTTPRequestHandler):
    do_POST = handle_post

def run_server():
    httpd = HTTPServer(('', 8555), handler)
    print 'Starting brain httpd server...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv
    run_server()

