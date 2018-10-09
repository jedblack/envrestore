from fabric.api import task, env
from fabric.colors import green, red

from fabfile.notify import adapter as notify
from fabfile.util import runner
from fabfile.lb.control import LbController

@task
def status(status_type=None):
    if status_type == 'depp':
        status = LbController(env.lb_host).status('depp')
        status = red(status, True) if status == LbController.DEPP_ON else green(status, True)
        print "depp state for %s is: %s" % (env.env, status)
    else:
        print LbController(env.lb_host).status()

@task
def depp():
    if LbController(env.lb_host).enable_depp():
        notify.announce('%s depped %s' % (runner(), env.env))
    else:
        print "failed to depp %s" % env.env

    status = LbController(env.lb_host).status('depp')
    status = red(status, True) if status == LbController.DEPP_ON else green(status, True)
    print "depp state for %s is: %s" % (env.env, status)

@task
def undepp():
    if LbController(env.lb_host).disable_depp():
        notify.announce('%s undepped %s' % (runner(), env.env))
    else:
        print "failed to undepp %s" % env.env

    status = LbController(env.lb_host).status('depp')
    status = red(status, True) if status == LbController.DEPP_ON else green(status, True)
    print "depp state for %s is: %s" % (env.env, status)
