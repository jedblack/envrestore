import socket, time
from fabfile.timeout import attempt_or_warn
from fabric.api import env, warn

def new(*args):
    return IRC(*args)

def error_handler(*args):
  env.notify_mute.append('irc')
  if len(args) > 1:
    warn("Disabling IRC notifications - operation failed: %s\n%s" % (args[1], args[2]))
  else:
    warn("Disabling IRC notifications.")

class IRC:
  HOST     = "irc.lipsum.com"
  PORT     = 6667
  NICK     = "DeployBotDeux"
  IDENT    = "DeployBotDeux"
  REALNAME = "DeployBotDeux"

  _instance = None

  DEPLOY_CHANNELS = ['#deploy']
  SYSOP_CHANNELS  = ['#sysops']
  BROAD_CHANNELS  = ["#develop"] + SYSOP_CHANNELS + DEPLOY_CHANNELS
  TEST_CHANNEL    = ['#test']

  def __new__(cls, *args):
    if not cls._instance:
      cls._instance = super(IRC, cls).__new__(cls, *args)
    return cls._instance

  def __init__(self):
    self.__setup()

  def __setup(self):
    with attempt_or_warn(5, timeout_handler = error_handler, exception_handler = error_handler):
      self.irc = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
      self.irc.connect((self.HOST, self.PORT))
      self.irc.send("NICK %s\r\n" % self.NICK)
      self.irc.send("USER %s %s bla :%s\r\n" % (self.IDENT, self.HOST, self.REALNAME))

  def __send(self,msg):
    try:
      self.irc.send(msg)
    except socket.error:
      self.__setup()
      self.irc.send(msg)

  def announce(self, message, channels=None):
    with attempt_or_warn(5, timeout_handler = error_handler, exception_handler = error_handler):
      if channels == None:
        channels = self.SYSOP_CHANNELS

      for channel in channels:
        self.__send("JOIN :%s\r\n" % channel)
        time.sleep(1)
        self.__send("PRIVMSG %s :%s\r\n" % (channel, message))

  def broad_announce(self, message):
      self.announce(message, self.BROAD_CHANNELS)

  def sysop_announce(self, message):
      self.announce(message, self.SYSOP_CHANNELS)

  def test_announce(self, message):
      self.announce(message, self.TEST_CHANNEL)
