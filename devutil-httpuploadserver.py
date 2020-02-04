#!/usr/bin/env python3

# Inspired by https://gist.github.com/touilleMan/eb02ea40b93e52604938
# Reduced to _only_ handle file uploads

import os
import http.server
import re

from http.server import HTTPServer, BaseHTTPRequestHandler


class UploadHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            self.directory = os.getcwd()
        else:
            self.directory = directory
        super().__init__(*args, **kwargs)

    def do_POST(self):
        r, info = self.handle_post_data()
        print((r, info, "by: ", self.client_address))
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(0))
        self.end_headers()

    def handle_post_data(self):
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if boundary not in line:
            return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(
                r'Content-Disposition.*name="file"; filename="(.*)"',
                line.decode())
        if not fn:
            return (False, "Can't find out file name...")
        fn = os.path.join(self.directory, fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn2 = re.findall(b'Content-Type:.*', line)
        if fn2:
            line = self.rfile.readline()
            remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False,
                    "Can't create file to write, do you have permission to "
                    "write?")

        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, "File '%s' upload success!" % fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.")


def test(
        HandlerClass=UploadHTTPRequestHandler,
        ServerClass=HTTPServer,
        port=8080,
        bind=""):
    http.server.test(
            HandlerClass=HandlerClass,
            ServerClass=ServerClass,
            port=port,
            bind=bind)


if (__name__ == '__main__'):
    import argparse
    from functools import partial

    # Mimic relevant arguments of SimpleHTTPRequestHandler
    # https://github.com/python/cpython/blob/3.7/Lib/http/server.py
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '--bind', '-b', default='', metavar='ADDRESS',
            help='Specify alternate bind address (default: all interfaces)')
    parser.add_argument(
            '--directory', '-d', default=os.getcwd(),
            help='Specify alternate directory (default: current directory)')
    parser.add_argument(
            'port', action='store', default=8000, type=int,
            nargs='?', help='Specify alternate port (default: %(default)s)')
    args = parser.parse_args()

    handler_class = partial(UploadHTTPRequestHandler, directory=args.directory)
    test(HandlerClass=handler_class, port=args.port, bind=args.bind)
