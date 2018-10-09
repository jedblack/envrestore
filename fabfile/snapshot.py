import re
from time import sleep
from fabric.api import task, env

from fabfile.sanclient import VnxClient, VnxConfig
from fabfile.util import benchmark

def object_name_from_host_env(format_string):
  host = re.sub('^[^@]+@', '', env.host_string)
  return format_string % '-'.join(host.split('.')[0:2])

@task
def recreate():
  '''Recreate the snapshot/mountpoint for the given host'''
  with benchmark('snapshot_recreate'):
    client = VnxClient(
      VnxConfig(
        dry_run = env.dry_run,
        debug = env.debugging,
        cli_path = '/usr/bin/sudo /opt/Navisphere/bin/naviseccli'
      )
    )

    mountpoint_name   = object_name_from_host_env("%s-smp")
    mountpoint_lun_id = client.get_lun_by_name(mountpoint_name).id

    snapshot_name   = object_name_from_host_env("%s-snap")
    snapshot_lun_id = client.get_snapshot_by_name(snapshot_name).primary_lun_s

    client.detach_snapshot(snapshot_name, mountpoint_lun_id)
    client.delete_snapshot(snapshot_name)

    sleep(15) # let the array cool down

    client.create_snapshot(snapshot_lun_id, snapshot_name)
    client.attach_snapshot(snapshot_name, mountpoint_lun_id)

    sleep(15) # let the array cool down

