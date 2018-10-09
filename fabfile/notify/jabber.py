import xmpp, os
from fabric.api import warn, env
from random import randint
from fabfile.timeout import attempt_or_warn

class ConnectionError(Exception): pass
class AuthorizationError(Exception): pass

def new(*args):
    return Jabber(*args)

def error_handler(*args):
  env.notify_mute.append('jabber')
  if len(args) > 1:
    warn("Disabling Jabber notifications - operation failed: %s\n%s" % (args[1], args[2]))
  else:
    warn("Disabling Jabber notifications.")

class Jabber():

    PASSWORD  = 'ENTER YOUR CREDS HERE'
    NICKNAME  = 'DeployBot'

    _instance = None

    DEPLOY_CHANNELS = [ 'deploy@conference.lipsum.com' ]
    SYSOP_CHANNELS  = [ 'systems@conference.lipsum.com' ] + DEPLOY_CHANNELS
    BROAD_CHANNELS  = [ 'develop@conference.lipsum.com' ] + SYSOP_CHANNELS
    TEST_CHANNEL    = [ 'test@conference.lipsum.com' ]

    def __new__(cls, *args):
        if not cls._instance:
            cls._instance = super(Jabber, cls).__new__(cls, *args)
        return cls._instance

    def __init__(self):
        self._jid       = xmpp.protocol.JID(self.jabber_id())
        self._client    = xmpp.Client(self._jid.getDomain(), debug=[]) # debug=['socket', 'bind', 'dispatcher'])
        self._connected = False

    def jabber_id(self):
        return "deploybot@lipsum.com/deploy.%s.%d" % (os.getpid(), randint(111111, 999999))

    def __connect_if_disconnected(self):
        if not self._connected:
            self.__connect()

    def __connect(self):
        with attempt_or_warn(5, timeout_handler = error_handler):
            try:
                result = self._client.connect()
                if result is None:
                    raise ConnectionError

                result = self._client.auth(self._jid.getNode(), self.PASSWORD, resource = self._jid.getResource())
                if result is None:
                    raise AuthorizationError

                self._client.sendInitPresence(requestRoster=0)

                self._connected = True

            except Exception as e:
                raise ConnectionError(e)

    def __send(self, to, msg):
        message = xmpp.protocol.Message(to, msg)
        message.setType('groupchat')

        try:
            self.__connect_if_disconnected()
            self._client.send(message)
        except:
            self.__connect() # try to connect again
            try:
                self._client.send(message)
            except:
                warn("Unable to send notification to %s" % to)

    def __join(self, channel):
        self.__connect_if_disconnected()
        self._client.send(xmpp.Presence(to="{0}/{1}".format(channel, self.NICKNAME)))

    def announce(self, message, channels=None):
        with attempt_or_warn(5, timeout_handler = error_handler):
            try:
                if channels == None:
                    channels = self.DEPLOY_CHANNELS

                for channel in channels:
                    self.__join(channel)
                    self.__send(channel, message)
            except (AuthorizationError, ConnectionError) as e:
                warn("Unable to connect to jabber service. skipping jabber notifications...")
                warn("Connection Error was %s" % e)
                pass

    def sysop_announce(self, message):
        self.announce(message, self.SYSOP_CHANNELS)

    def broad_announce(self, message):
        self.announce(message, self.BROAD_CHANNELS)

    def test_announce(self, message):
        self.announce(message, self.TEST_CHANNEL)

def shutdown_jabber():
    Jabber().shutdown()
