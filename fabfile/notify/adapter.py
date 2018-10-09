from fabric.api import env
from fabfile.notify import jabber, irc

def announce(message, method = 'announce'):
    types = { 'jabber': jabber, 'irc': irc }
    for _type, adapter in types.iteritems():
        if _type in env.notify_mute: continue
        if env.notify_using in [ _type, 'all' ]:
            _method = getattr(adapter.new(), method)
            if callable(_method) and not _type in env.notify_mute:
                _method(message)

def broad_announce(message):
    announce(message, 'broad_announce')

def sysop_announce(message):
    announce(message, 'sysop_announce')

def test_announce(message):
    announce(message, 'test_announce')
