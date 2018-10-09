#!/usr/bin/env python
# Author : Friedrich Seifts <fseifts@gmail.com>

import pexpect, sys, datetime, argparse, time, os, fabric
from fabric.api import *
from subprocess import call

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--lipsumenv', nargs='*', required=True, type=str, choices=['qa2', 'dev1', 'dev2', 'dev3'], help='Environments to perform restore operation, requires at least one environment to run')
parser.add_argument('-d', '--debug', default="False", action="store_true", help='Turns debug output on (default = off)')
parser.add_argument('-w', '--warn_only', default="False", action="store_true", help='Turns on "warnings-only", which allow processing to continue on any errors (default = off)')

currenttime   = datetime.datetime.now()
array         = "vnx.nyc.lipsum.com"
seckey        = "/opt/Navisphere/seckey"
sqlinit       = "/etc/mysql/init.sql"
navibin       = "/opt/Navisphere/bin/naviseccli"
lipsumenv       = parser.parse_args().lipsumenv
debugset      = parser.parse_args().debug
env.warn_only = parser.parse_args().warn_only
dbhosts       = ['mongo01', 'mysql01']
fehosts       = ['web01', 'php01']
domain        = "lipsum.com"
env.user      = "envrestore"
sleeptime     = {'high' : 15, 'medium': 10, 'low' : 5}
line          = "-" * 50
mongo_hosts   = []
mysql_hosts   = []
web_hosts     = []
php_hosts     = []


if debugset == True:
  fabric.state.output.debug   = True
  fabric.state.output.running = True
  fabric.state.output.stdout  = True
  fabric.state.output.stderr  = True
else:
  fabric.state.output.debug   = False
  fabric.state.output.running = False
  fabric.state.output.stdout  = False
  fabric.state.output.stderr  = False


# Leaving Logger class off for now, fabric is calling .isatty() method which Logger pukes on.  Using {cron job} >> /var/log/envrestore/envrestore.log for the time being.
'''
class Logger(object):
    def __init__(self):
        self.stgout = sys.stdout
        self.stderr   = sys.stderr
        self.log = open("/var/log/envrestore/envrestore.log", "a")

    def write(self, message):
        self.stgout.write(message)
        self.stderr.write(message)
        self.log.write(message)

sys.stdout = Logger()
sys.stderr = Logger()
'''


# !! DO NOT CHANGE IDs !!
mongo_plunid = 3
mysql_plunid = 4

smp_dict = {
  'mysql_dev3smp_lunid' : 4015,
  'mysql_dev2smp_lunid' : 4016,
  'mysql_dev1smp_lunid' : 4017,
  'mongo_dev3smp_lunid' : 4018,
  'mongo_dev2smp_lunid' : 4019,
  'mongo_dev1smp_lunid' : 4020,
  'mongo_qa2smp_lunid'  : 4021,
  'mysql_qa2smp_lunid'  : 4080,
}
# !! DO NOT CHANGE IDs !!


def run_time():
  global runtime
  runtime = datetime.datetime.now()

def gen_fab_hosts():
  for e in lipsumenv:
    for h in dbhosts:
      if "mysql" in h:
        host = "%s.%s.%s" % (h, e, domain)
        mysql_hosts.append(host)
      elif "mongo" in h:
        host = "%s.%s.%s" % (h, e, domain)
        mongo_hosts.append(host)
  env.roledefs['mongo'] = mongo_hosts
  env.roledefs['mysql'] = mysql_hosts

  for e in lipsumenv:
    for h in fehosts:
      if "web" in h:
        webhost = "%s.%s.%s" % (h, e, domain)
        web_hosts.append(webhost)
      elif "php" in h:
        phphost = "%s.%s.%s" % (h, e, domain)
        php_hosts.append(phphost)
  env.roledefs['web'] = web_hosts
  env.roledefs['php'] = php_hosts


def delete_snap(env="", host=""):
  child = pexpect.spawn('%(a)s -secfilepath %(b)s -h %(c)s snap -destroy -id %(d)s-%(e)s-snap' % {'a':navibin, 'b':seckey, 'c':array, 'd':host, 'e':env})
  child.expect('Are you sure you want to perform this operation\?\(y\/n\):')
  child.sendline('y')
  child.sendcontrol('m')


def create_snap(env="", host="", lunid=""):
  os.system("%(a)s -secfilepath %(b)s -h %(c)s snap -create -res %(d)s -name %(e)s-%(f)s-snap -allowReadWrite yes" % {'a':navibin, 'b':seckey, 'c':array, 'd':lunid, 'e':host, 'f':env})


def smp_ops(env="", host="", lunid="", smpaction=""):
  os.system("%(a)s -secfilepath %(b)s -h %(c)s snap -%(d)s -id %(e)s-%(f)s-snap -res %(g)s" % {'a':navibin, 'b':seckey, 'c':array, 'd':smpaction, 'e':host, 'f':env, 'g':lunid})


def run_delete_snap():
  print "Destroying block level snapshots"
  for e in lipsumenv:
    for h in dbhosts:
      delete_snap(env=e, host=h)
  print "Destroy block level snapshots completed"


def run_create_snap():
  print "Creating block level snapshots"
  for e in lipsumenv:
    for h in dbhosts:
      if "mysql" in h:
        create_snap(env=e, host=h, lunid=mysql_plunid)
      elif "mongo" in h:
        create_snap(env=e, host=h, lunid=mongo_plunid)
  print "Creation of block level snapshots completed"


def run_smp_ops(smpaction=""):
  for e in lipsumenv:
    for h in dbhosts:
      if "mysql" in h:
        smp_ops(env=e, host=h, lunid=smp_dict['mysql_%ssmp_lunid' % e], smpaction=smpaction)
      elif "mongo" in h:
        smp_ops(env=e, host=h, lunid=smp_dict['mongo_%ssmp_lunid' % e], smpaction=smpaction)


@roles('php')
def phprestart():
    sudo('service php-fpm restart')


@roles('web')
def webrestart():
    sudo('service varnish restart')
    sudo('service nginx restart')


@roles('mongo')
def mongo_env_bootstrap(action=""):
  if "stop" in action:
    print "Force killing all mongod processes"
    sudo('pkill -9 mongod')

    print "Force killing potential hijacks on mongo data directory"
    sudo('for p in $(lsof /var/lib/mongo |awk \'{print $2}\' |more +2); do kill -9 $p ; done')

    print "Un-mount mongo data location"
    sudo('umount /var/lib/mongo')

  elif "start" in action:
    print "Mounting mongo data location"
    sudo('mount /dev/sdb1 /var/lib/mongo')

    print "Deleting mongo lock file, and journals"
    sudo('rm -f /var/lib/mongo/mongod.lock')
    sudo('rm -rf /var/lib/mongo/journal')

    print "Starting mongod server process"
    sudo('service mongod start')
  else:
    print "Invalid action defined for mongo bootstrap"


@roles('mysql')
def mysql_env_bootstrap(action=""):
  if "stop" in action:
    sudo('rm -f /tmp/envrestore.sql')
    print "Force killing all mysqld processes"
    sudo('pkill -9 mysql')

    print "Force killing potential hijacks on mysql data directory"
    sudo('for p in $(lsof /var/lib/mysql |awk \'{print $2}\' |more +2); do kill -9 $p ; done')

    print "Un-mount mysql data location"
    sudo('umount /var/lib/mysql')

  elif "start" in action:
    print "Mounting mysql data location"
    sudo('mount /dev/sdb1 /var/lib/mysql')

    print "Removing master.info replication file"
    sudo('rm -f /var/lib/mongo/master.info')

    print "Setting mysql credentials for environment"
    sudo('mysqld_safe --init-file=%s &' % (sqlinit))
    time.sleep(sleeptime['high'])
    sudo('rm -f /tmp/envrestore.sql')
    sudo('pkill -9 mysql')

    print "Starting mysql server process"
    sudo('service mysql start')
  else:
    print "Invalid action defined for mysql bootstrap"


gen_fab_hosts()


run_time()
print "Environment restore started at: %s" % (runtime)
print line


execute(mongo_env_bootstrap, action="stop")
execute(mysql_env_bootstrap, action="stop")
run_smp_ops(smpaction="detach")
run_delete_snap()
print "Maintain holding pattern for %d seconds, allowing array to process destroy task" % (sleeptime['high'])
time.sleep(sleeptime['high'])


run_create_snap()
run_smp_ops(smpaction="attach")
print "Maintain holding pattern for %d seconds, allowing array to process creation task" % (sleeptime['high'])
time.sleep(sleeptime['high'])
execute(mongo_env_bootstrap, action="start")
execute(mysql_env_bootstrap, action="start")
print "Maintain holding pattern for %d seconds, allowing data tier to come online before connecting web/php nodes" % (sleeptime['medium'])
time.sleep(sleeptime['medium'])


print "Restarting php"
execute(phprestart)
print "Maintain holding pattern for %d seconds, allowing php to come online before restarting web/php nodes" % (sleeptime['low'])
time.sleep(sleeptime['low'])
print "Restarting nginx, and varnish"
execute(webrestart)


run_time()
print line
print "Environment restore ended at: %s" % (runtime)
