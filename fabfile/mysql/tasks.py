from contextlib import contextmanager, nested
from fabric.api import sudo, task, roles, execute, puts, hide, settings, abort, env
from fabfile.util import benchmark

__all__ = [ 'restore' ]

@contextmanager
def mysql(init_file='/etc/mysql/init.sql'):
  try:
    with benchmark('mysql_stop'):
      with nested(hide('output','running','warnings'), settings(warn_only=True)):
        puts('Waiting for MySQLD to finish shutting down...')
        sudo("""
          seconds=30;
          while [ $seconds -gt 0 ]; do
            lsof -t /var/lib/mysql &>- && for p in $(lsof -t /var/lib/mysql); do kill -9 $p; done || exit 0;
            sleep 1;
            seconds=$((seconds - 1));
          done;
          exit 2
        """)
      sudo('umount /var/lib/mysql')
      yield
  finally:
    with benchmark('mysql_start'):
      sudo('mount /dev/sdb1 /var/lib/mysql')
      sudo('rm -f /var/lib/mongo/master.info')
      sudo('nohup mysqld --init-file=%s &>/tmp/reinit.log &' % (init_file))
      puts('Waiting for MySQLD to finish initializing...')
      with nested(hide('output','running','warnings'), settings(warn_only=True)):
        sudo("""
          seconds=30;
          while [ $seconds -gt 0 ]; do
            grep -qP "^Version.+socket:.+port:.+" /tmp/reinit.log && pkill -9 mysql && exit 0;
            grep -qP "(Aborting|Starting shutdown)" /tmp/reinit.log && exit 1;
            sleep 1;
            seconds=$((seconds - 1));
          done;
          exit 2
        """)
      sudo('service mysql start')

@task
@roles('mysql')
def restore(init_file='/etc/mysql/init.sql'):
  '''Performs a restore of the MySQL database for the given environment'''
  if not env.roledefs['mysql'] or len(env.roledefs['mysql']) == 0:
    abort("Unable to find MySQL server(s) to perform restore on - quitting!")

  with benchmark('mysql_restore'):
    with mysql(init_file):
      puts("running snapshot recreate")
      execute('snapshot.recreate')
