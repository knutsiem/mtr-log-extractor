#!/usr/bin/env python3

import sys
import requests

filename = sys.argv[1]
url = sys.argv[2]
with open(filename, 'rb') as f:
    r = requests.post(url, files={'file': f})
