#!/usr/bin/env python3

'''
CCP ESI (basic module to communicate with the EVE Swagger Interface)
Copyright (C) 2018 Christian Rickert <mail@crickert.de>
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''


# imports

import http.server
import json
import urllib.request
import http


# variables

CLIENT_REQUEST = ""  # contains the authentication code


# functions

def get_listener(address, port):
    ''' Starts a HTTP server that returns an incoming request to a given port as string. '''

    global CLIENT_REQUEST
    http.server.HTTPServer.timeout = 60  # seconds

    class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
        ''' Overriding the basic logging function to get the client's request. '''

        global CLIENT_REQUEST

        def log_message(self, format, *args):  # overriding to extract client request
            global CLIENT_REQUEST
            CLIENT_REQUEST, *rest = args

        def do_GET(self):
            ''' Handles the output stream for writing a response back to the client.  '''
            self.send_response(http.HTTPStatus.OK)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("Authentication code received! " +\
                                   "You can close this window now.", "utf-8"))

    httpd = http.server.HTTPServer((address, port), CustomHTTPRequestHandler)
    httpd.handle_request() # single request only

    try:
        return str(CLIENT_REQUEST)
    except NameError:  # 'CLIENT_REQUEST' not defined within timeout
        return None


def get_request(url, headers, data=None):
    ''' Performs GET and POST requests and returns the server's response with dictionaries. '''

    url = str(url)
    headers = dict(headers)
    if data:  # POST: read data from and write data to server
        data = urllib.parse.urlencode(data).encode(encoding="utf-8", errors="replace")
    else:     # GET:  read data from server only
        pass

    set_request = urllib.request.Request(url, headers=headers, data=data)
    open_url = urllib.request.urlopen(set_request)
    server_response = json.loads(open_url.read().decode('utf-8'))  # native Python objects

    return server_response if server_response else None


def read_api(api_request, return_key, *search_pairs):
    ''' Returns the first value from an API request that matches the maximum number of key/value pairs. '''

    index = 0  # iteration position of the API dictionary
    maxmatches = 0  # maximum number of dictionary entries matching criteria
    best_index = 0  # index of the API dictionary with best matching criteria

    for api_dictionary in api_request:  # iterate through API dictionaries
        matches = []
        for api_key, api_value in api_dictionary.items():  # iterate through API key/value pairs
            for search_key, search_value in search_pairs:
                if api_key == search_key and api_value == search_value:
                    matches.append(True)
                else:
                    matches.append(False)
        if matches.count(True) > maxmatches:
            best_index = index
            maxmatches = matches.count(True)
        index += 1

    return api_request[best_index][return_key] if maxmatches else None
