# Sublime Text 2 Settings
# sublime: x_syntax Packages/Python/Python.tmLanguage
# sublime: translate_tabs_to_spaces true
# sublime: tab_size  2

import requests

class LbController:
  DEPP_ON   = 'on'
  DEPP_OFF  = 'off'
  DEPP_FLIP = 'flip'

  REQUEST_HEADERS = {
    'lipsum-Auth':  'FILL IN YOU AUTH KEY',
    'User-Agent': 'Lipsum Deployer',
  }

  HOST_IP_MAP = {
    'www.lipsum.com': 'www1.lipsum.com',
    'stg.lipsum.com': 'stg.lipsum.com'
  }

  __instance = {}

  def __new__(cls, api_host):
    if not cls.__instance[api_host]:
      cls.__instance[api_host] = super(LbController, cls).__new__(cls, api_host)
    return cls.__instance[api_host]

  def __init__(self, host):
    self.headers  = dict(self.REQUEST_HEADERS.items() + {'Host': host }.items())
    self.lb_ip    = self.HOST_IP_MAP[host]

  def __url(self, uri):
    return "https://%s/f5/%s" % (self.lb_ip, uri)

  def __put(self, uri):
    return requests.put(self.__url(uri), headers=self.headers)

  def __get(self, uri):
    return requests.get(self.__url(uri), headers=self.headers)

  def enable_depp(self):
    self.__put('depp/%s' % self.DEPP_ON)
    return self.status('depp') == self.DEPP_ON

  def disable_depp(self):
    self.__put('depp/%s' % self.DEPP_OFF)
    return self.status('depp') == self.DEPP_OFF

  def status(self, type = None):
    if type == 'depp':
      return self.__get('status/depp').text.strip()
    else:
      return self.__get('status').text.strip()

