'''
Examples:

  Restore the given environments:
    $ fab restore:envA,envB,envC

  Simulate VNX operations:
    $ fab dry_run:on restore:envA
'''

from fabric.api import env, task, runs_once, abort
from fabric.state import output
import pprint

# if we are in debug mode, make sure we are verbose with ssh logging too
env.debugging = False
if output['debug']:
    env.debugging = True
    import logging
    logging.basicConfig()
    logging.getLogger('ssh.transport').setLevel(logging.DEBUG)

ENVIRONMENTS = {
  'development' : 'dev',
  'qa'          : 'qa',
  'laboratory'  : 'lab'
}


env.navisphere    =  {
  'sekkey' : '/opt/Navisphere/seckey',
  'navibin': '/opt/Navisphere/bin/naviseccli'
}

# settings
env.env       = None
env.env_short = None
env.user      = 'envrestore'

env.sql_initfile = "/etc/mysql/init.sql"

env.lb_host   = 'www.lipsum.com'

env.interact  = True
env.benchmark = True
env.dry_run   = False

env.depp_on_update = True
env.allow_update   = True
env.abort_on_prompts = True

# notifications
env.notify_using = 'jabber' # jabber, irc, or all
env.notify_mute  = []

# roles
env.roledefs['mysql'] = []
env.roledefs['mongo'] = []
env.roledefs['web']   = []
env.roledefs['php']   = []

import fabfile.lb.tasks as lb
import fabfile.notify.tasks as notify
import fabfile.restore.tasks as restore
import fabfile.mongo.tasks as mongo
import fabfile.mysql.tasks as mysql
import fabfile.snapshot as snapshot
import fabfile.services as services
import fabfile.util as util

from fabfile.restore.tasks import restore

@task
@runs_once
def benchmark(v='on'):
  '''
  Enables or disables benchmarking of deploy tasks
  '''
  env.benchmark = v.lower() in [ 'true', 'yes', 'on', '1' ]

@task
@runs_once
def dry_run(v='on'):
  '''
  Enables or disables performing of a dry run of the tasks that follow
  '''
  env.dry_run = v.lower() in [ 'true', 'yes', 'on', '1' ]

@task
def status():
  '''
  Outputs the status
  '''
  # execute('lb.status')

@task
@runs_once
def runner(runner):
  '''
  Set the name of the person performing the operation
  '''
  env.runner = runner

@task
@runs_once
def interact(interact=True):
  '''
  Enable or disable interation
  '''
  env.interact = interact in [True, 'true', 'yes', '1']

@task
@runs_once
def list_servers(which='all'):
  '''Lists the found servers for the given type (or all) in the current environment'''
  if 'all' in which:
    which = ['php', 'web', 'mysql', 'mongo']
  else:
    which = re.compile('\s*,\s*').split(which)

  servers = util.flatten([env.roledefs[group] for group in which])

  if len(servers) == 0:
    abort("No servers found. Did you select an environment first?")

  print "\nResponding Servers Found in [%s]:\n" % env.env.upper()
  for server in servers:
    print "\t%s" % server.split('@')[1]

@task
@runs_once
def dump():
  '''Dump current environment to the screen'''
  pprint.PrettyPrinter(indent=4, depth=3).pprint(env)

@task(alias='env')
def setenv(name, short_name = None):
  '''Sets the current environment to the given value'''
  env.env       = name
  env.env_short = ENVIRONMENTS[name] if name in ENVIRONMENTS else name

  # load balancer host
  env.lb_host     = '%s.lipsum.com' % env.env_short

  env.roledefs['mysql'] = util.mysql_server_list(max_node_index=5)
  env.roledefs['mongo'] = util.mongo_server_list(max_node_index=5)
  env.roledefs['web']   = util.web_server_list(max_node_index=5)
  env.roledefs['php']   = util.php_server_list(max_node_index=5)
