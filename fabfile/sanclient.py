import pprint
import re

from fabfile.util import local_command, volatile_command

__all__ = ['Lun', 'VnxConfig', 'VnxClient']

def convert_to_number(s):
  try:
    s = s.strip('%$')
    if int(float(s)) != float(s):
      return float(s)
    else:
      return int(float(s))
  except ValueError:
    raise TypeError('unable to convert non-numeric value to number')

class SanObject:
  '''
  Represents a SAN object in a very simple form
  '''
  def to_string(self):
    return "<%s name='%s'>" % (self.__class__.__name__, int(self.id), self.name, int(self.size))

  def repr(self):
    return repr(self.to_string())

  def __str__(self):
    return self.to_string()

  def __getitem__(self, key):
    return getattr(self, key)

  def __setitem__(self, key, value):
    return setattr(self, key, value)

  def properties(self):
    return self.__dict__.items()

  def add_property(self, propname, value):
    propname = re.sub('[^\w]+', '_', propname)
    propname = re.sub('_+$', '', propname).lower()

    try:
      value = convert_to_number(value)
    except TypeError:
      if value.lower() in ('true', 'false', 'yes', 'no'):
        value = False if value.lower() in ('false', 'no') else True

    return setattr(self, propname, value)

  def dump(self):
    pprint.PrettyPrinter(indent=4, depth=3).pprint(vars(self))

class Lun(SanObject): pass
class Snapshot(SanObject): pass

class VnxConfig:
  '''
  Top-level interface for SAN configs
  '''

  _management_endpoints = ['vnx.nyc.lipsum.com']
  _data_endpoints       = []
  _cli_path             = '/opt/Navisphere/bin/naviseccli'
  _username             = ''
  _password             = ''
  _secfilepath          = '/opt/Navisphere/seckey'
  _debug                = False
  _dry_run              = True

  @property
  def management_endpoints(self): return self._management_endpoints

  @property
  def data_endpoints(self): return self._data_endpoints

  @property
  def cli_path(self): return self._cli_path

  @property
  def username(self): return self._username

  @property
  def password(self): return self._password

  @property
  def secfilepath(self): return self._secfilepath

  @property
  def debug(self): return self._debug

  @property
  def dry_run(self): return self._dry_run

  def __getitem__(self, key):
    return getattr(self, key)

  def __init__(self, **kwargs):
    for attrname, value in kwargs.items():
      attribute = getattr(self, attrname)

      if type(attribute) == type([]):
        value = value if hasattr(value, '__iter__') else [value]
      elif type(attribute) == type(True):
        value = bool(value)

      setattr(self, attrname, value)

  def dump(self):
    pprint.PrettyPrinter(indent=4, depth=3).pprint(vars(self))

class VnxClient(object):
    '''
    VNX implementation of the SANClient
    '''
    LUN_DELIMITER              = 'LOGICAL UNIT NUMBER'

    _config    = None
    _cmd_base  = []
    _luns      = []
    _snapshots = []

    @property
    def config(self):
      return self._config

    @property
    def cmd_base(self):
      return self._cmd_base

    def get_luns(self, force = False):
      '''Gets list of all Luns'''
      if force or len(self._luns) <= 0:
        command = self._build_command(['lun', '-list'])
        with local_command(command) as result:
          self._luns = [self._parse_lun_record(record) for record in self._parse_object_list(result)]
      return self._luns
    luns = property(fget = get_luns)

    def get_snapshots(self, force = False):
      '''Get list of all Snapshots'''
      if force or len(self._snapshots) <= 0:
        command = self._build_command(['snap', '-list', '-detail'])
        with local_command(command) as result:
          self._snapshots = [self._parse_snapshot_record(record) for record in self._parse_object_list(result)]
      return self._snapshots
    snapshots = property(fget = get_snapshots)

    def __init__(self, config=None):
      self._config = config if config else VnxConfig()
      self.get_luns(True)
      self.get_snapshots(True)

    def __getitem__(self, id_or_name):
      try:
        if type(id_or_name) == type(1):
          _id = id_or_name
        else:
          _id = convert_to_number(id_or_name)
        return self.get_lun_by_id(_id)
      except TypeError:
        return self.get_lun_by_id(id_or_name)

    def _debugging(self):
      self._config.debug

    def _build_command(self, cmd):
      if (len(self._cmd_base) == 0):
        self._cmd_base = [
          self._config.cli_path,
          '-Address', self._config.management_endpoints[0]
        ]

        if self._config.secfilepath and len(self._config.secfilepath) > 0:
          self._cmd_base = self._cmd_base + ['-secfilepath', self._config.secfilepath]
        else:
          self._cmd_base = self._cmd_base + [
            '-User', self._config.username,
            '-Password', self._config.password,
            '-Scope', '0'
          ]

      return ' '.join(self._cmd_base + cmd)

    def _parse_object_list(self, output):
      '''Constructs a list of objects from the given input string'''
      for record in re.compile('\n{2,}').split(output):
        yield record

    def _parse_lun_record(self, lun_record):
      lun = Lun()
      for line in [l.strip() for l in lun_record.splitlines()]:
        if line.startswith(self.LUN_DELIMITER):
          lun.id = int(line.split(' ')[-1])
        else:
          lun.add_property(*re.compile('\s*:\s*').split(line, 1))
      return lun

    def _parse_snapshot_record(self, snapshot_record):
      snapshot = Snapshot()
      for line in [l.strip() for l in snapshot_record.splitlines()]:
        snapshot.add_property(*re.compile('\s*:\s*').split(line, 1))
      return snapshot

    def _find_lun_by_property_key_and_value(self, key, value):
      for record in self._luns:
        for k, v in record.properties():
          if (k,v) == (key, value):
            return record
      return None

    def _find_snapshot_by_property_key_and_value(self, key, value):
      for record in self._snapshots:
        for k, v in record.properties():
          if (k,v) == (key, value):
            return record
      return None

    def get_lun_by_id(self, lun_id, direct=False):
      if not direct:
        return self._find_lun_by_property_key_and_value('id', lun_id)

      command = self._build_command(['lun', '-list', '-id', str(lun_id)])
      with local_command(command) as result:
        return self._parse_lun_record(result.strip())

    def get_lun_by_name(self, lun_name, direct=False):
      if not direct:
        return self._find_lun_by_property_key_and_value('name', lun_name)

      command = self._build_command(['lun', '-list', '-name', str(lun_name)])
      with local_command(command) as result:
        return self._parse_lun_record(result.strip())

    def get_snapshot_by_name(self, snapshot_name, direct=False):
      if not direct:
        return self._find_snapshot_by_property_key_and_value('name', snapshot_name)

      command = self._build_command(['snap', '-list', '-id', str(snapshot_name)])
      with local_command(command) as result:
        return self._parse_snapshot_record(result.strip())

    def create_snapshot(self, lun_id, snapshot_name):
      command = self._build_command(['snap', '-create', '-res', str(lun_id), '-restype', 'lun', '-name', snapshot_name, '-allowReadWrite', 'yes'])
      with volatile_command(command) as result:
        return result.succeeded

    def delete_snapshot(self, snapshot_name):
      command = self._build_command(['snap', '-destroy', '-id', snapshot_name, '-o'])
      with volatile_command(command) as result:
        return result.succeeded

    def attach_snapshot(self, snapshot_name, mount_point):
      command = self._build_command(['snap', '-attach', '-id', str(snapshot_name), '-res', str(mount_point)])
      with volatile_command(command) as result:
        return result.succeeded

    def detach_snapshot(self, snapshot_name, mount_point):
      command = self._build_command(['snap', '-detach', '-id', snapshot_name, '-res', str(mount_point)])
      with volatile_command(command) as result:
        return result.succeeded
