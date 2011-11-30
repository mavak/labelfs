#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse

import URIGraph

urigraph = URIGraph.URIGraph("%s/.lfs/lfs.graph" % os.path.expanduser('~'))

class MyHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    qs = {}
    path = self.path
    if '?' in path:
      path, tmp = path.split('?', 1)
      qs = urlparse.parse_qs(tmp)
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    nodes=[]
    if qs['q'][0] != "":
      uris = {}
      for uri in urigraph.query(qs['q'][0]):
        uris[uri] = 1
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
