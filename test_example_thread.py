import time
from proxyserver import MITMProxyRunThread

MITMProxyRunThread(8080, 'mitmproxy').start()

time.sleep(10)