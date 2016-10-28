import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from pprint import pprint

class S(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        for d in data:
            print d.get("time"), d.get("host"), d.get("plugin"), d.get("type"), d.get("type_instance"), d.get("plugin_instance"), d.get("dsnames"), d.get("values")
            #pprint(d)
        self.wfile.write("true")

def run(server_class=HTTPServer, handler_class=S, port=8555):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting brain httpd server...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

if len(argv) == 2:
    run(port=int(argv[1]))
else:
    run()
