from fabric.api import task, runs_once, roles, parallel, env
from fabric.api import execute, sudo

from fabfile.notify import sysop_announce
from fabfile.util import benchmark

__all__ = [ 'restart', 'backend', 'frontend' ]

@task
@runs_once
def restart():
  '''Restart both frontend and backend services'''
  with benchmark('services.restart'):
    if env.roledefs['php'] and len(env.roledefs['php']):
      execute('services.backend')

    if env.roledefs['web'] and len(env.roledefs['web']):
      execute('services.frontend')


@task
@parallel
@roles('php')
def backend():
  '''Restart backend services'''
  with benchmark('backend'):
    sudo('service php-fpm restart')

@task
@parallel
@roles('web')
def frontend():
  '''Restart frontend services'''
  with benchmark('frontend'):
    sudo('service nginx restart')
    sudo('service varnish restart')
