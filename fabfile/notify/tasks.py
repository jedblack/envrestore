from fabric.api import task, runs_once, env, abort
from adapter import announce
from fabfile.util import runner

@task
@runs_once
def mute(*types):
    '''
    Mute Notification Announcements
    '''
    if not types:
        env.notify_mute = ['irc', 'jabber']
    else:
        env.notify_mute = list(types)

@task
@runs_once
def using(v):
    '''
    Service to send notifications through (all, jabber, or irc)
    '''
    if not v.lower() in ['all', 'jabber', 'irc']:
        abort("Invalid notification service selection: must be one of 'all', 'jabber', or 'irc'")
    env.notify_using = v.lower()

@task
@runs_once
def test(message):
    '''
    Emits a test message to the default announcement channels
    '''
    announce("Test Message emitted by %s: %s" % (runner(), message))
