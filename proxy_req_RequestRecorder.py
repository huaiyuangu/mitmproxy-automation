"""
This example shows two ways to redirect flows to other destinations.
"""

import json

# global storage
import global_config


class RequestContentRecorder:
    def __init__(self):
        self.host = 'vortex.huluqa.com'

        print ('''
        ==== Request content Recorder was initialized ====
        
        ''')

    def request(self, flow):
        # https://vortex.hulu.com/api/v3/event
        s = flow.request.pretty_host
        if self.host == s:
            c = flow.request.data.content
            e, usr_id = (None, None)
            if len(c) > 0:
                d = json.loads(c)
                if 'event' in d:
                    for coo in flow.request.cookies.fields:
                        if '_hulu_pid' in coo:
                            usr_id = coo[1]
                    e = d['event']
                    if e == "player_heartbeat":
                        pass
                    else:
                        if usr_id not in global_config.TEST_EVENTS_DATA:
                            global_config.TEST_EVENTS_DATA[usr_id] = []
                        global_config.TEST_EVENTS_DATA[usr_id].append(e)
            print ('beacon recorder got usr id %s event %s' % (usr_id, str(e)))