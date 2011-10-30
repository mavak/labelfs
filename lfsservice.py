#!/usr/bin/python
# -*- coding: utf-8 -*-
import lfsengine
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse

le = lfsengine.LabelEngine("/home/gerard/lfs-store/lfs.shelve")

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Just received a GET request")
        qs = {}
        path = self.path
        if '?' in path:
          path, tmp = path.split('?', 1)
          qs = urlparse.parse_qs(tmp)
        print path, qs
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        nodes=[]
        if qs['q'][0] != "":
          nodes = {}
          for node in le.query(qs['q'][0]):
            nodes[node['name']] = node
          print "nodes=",nodes
          self.wfile.write(nodes)
        return

if __name__ == "__main__":
    try:
        server = HTTPServer(('localhost', 8000), MyHandler)
        print('Started http server')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
