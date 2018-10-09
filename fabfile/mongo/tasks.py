from contextlib import contextmanager, nested
from fabric.api import sudo, settings, task, roles, execute, puts, hide, settings, abort, env
from fabfile.util import benchmark

__all__ = [ 'restore' ]

@contextmanager
def mongo():
  try:
    with benchmark('mongo_stop'):
      puts('Waiting for MongoD to finish shutting down...')
      with nested(hide('output','running','warnings'), settings(warn_only=True)):
        sudo("""
          seconds=30;
          while [ $seconds -gt 0 ]; do
            lsof -t /var/lib/mongo &>- && for p in $(lsof -t /var/lib/mongo); do kill -9 $p; done || exit 0;
            sleep 1;
            seconds=$((seconds - 1));
          done;
          exit 2
        """)
      sudo('umount /var/lib/mongo')
      yield
  finally:
    with benchmark('mongo_start'):
      sudo('mount /dev/sdb1 /var/lib/mongo')
      sudo('rm -rf /var/lib/mongo/mongod.lock /var/lib/mongo/journal')
      sudo('service mongod start')

@task
@roles('mongo')
def restore():
  '''Performs a restore of the Mongo database for the given environment'''
  if not env.roledefs['mongo'] or len(env.roledefs['mongo']) == 0:
    abort("Unable to find Mongo server(s) to perform restore on - quitting!")

  with benchmark('mongo_restore'):
    with mongo():
      execute('snapshot.recreate')
