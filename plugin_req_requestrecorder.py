"""
This example shows two ways to redirect flows to other destinations.
"""

import json

# global storage
import global_config


class RequestContentRecorder:
    def __init__(self):
        self.host = 'www.google.com'

    def request(self, flow):
        s = flow.request.pretty_host
        if self.host == s:
            c = flow.request.data.content
            e, usr_id = (None, None)
            if len(c) > 0:
                d = json.loads(c)
                print "content is %s" % c
