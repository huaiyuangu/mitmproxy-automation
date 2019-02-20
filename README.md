# run mitmproxy to capture network traffics as background in automation testing


### how to setup
```
sudo pip install mitmproxy
```

### call MITMProxyRunThread in python code
```
import time
from proxyserver import MITMProxyRunThread

MITMProxyRunThread(8080, 'mitmproxy', plugin=['plugin_req_requestrecorder']).start()

time.sleep(10)
```



