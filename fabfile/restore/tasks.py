import re

from fabric.api import task, runs_once, env
from fabric.api import execute, sudo, abort, warn

from fabfile.notify import sysop_announce
from fabfile.util import benchmark, runner, flatten

__all__ = [ ]

def split_environments(*e):
  if len(e) == 0: return None
  return set(flatten( re.compile('\s*,\s*').split(','.join(e)) ))

@task
@runs_once
def restore(*_environ):
  '''
  Restore the given environment(s)
  '''
  _environ = split_environments(*_environ)

  if not _environ or len(_environ) == 0:
    if not env.env:
      abort("No environment(s) selected (_environ was %s)." % _environ)
    else:
      warn("restoring environment: %s" % env.env)
      _environ = set([env.env])

  with benchmark('restore'):
    for _env in _environ:
      # sysop_announce("%s is restoring mysql/mongo in environment %s" % (runner(), _env))
      execute('setenv', _env)
      for task in [ 'mongo.restore', 'mysql.restore', 'services.restart' ]:
        execute(task)
