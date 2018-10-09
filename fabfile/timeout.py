# Sublime Text 2 Settings
# sublime: x_syntax Packages/Python/Python.tmLanguage
# sublime: translate_tabs_to_spaces true
# sublime: tab_size  2

from contextlib import contextmanager
import errno, os, signal, traceback, sys
from fabric.api import warn, abort

class TimeoutError(Exception): pass

DEFAULT_TIMEOUT_SECOND = 10

@contextmanager
def timeout(seconds = DEFAULT_TIMEOUT_SECOND, error_message = os.strerror(errno.ETIME)):
  def _handle_timeout(signum, frame):
    raise TimeoutError(error_message)

  signal.signal(signal.SIGALRM, _handle_timeout)
  signal.alarm(seconds)
  try:
    yield seconds
  finally:
    signal.alarm(0)

@contextmanager
def attempt_or_warn(seconds = DEFAULT_TIMEOUT_SECOND, timeout_handler = None, exception_handler = None):
  try:
    with timeout(seconds):
      yield
  except TimeoutError:
    if not hasattr(timeout_handler, '__call__'):
      warn("Operation timed out after %d seconds.")
    else:
      timeout_handler(seconds)
  except Exception, e:
    trace = ''.join(traceback.format_tb(sys.exc_info()[2]))
    if not hasattr(exception_handler, '__call__'):
      warn("Operation failed: %s\n%s" % (e, trace))
    else:
      exception_handler(seconds, e, trace)

@contextmanager
def attempt_or_fail(seconds = DEFAULT_TIMEOUT_SECOND, timeout_handler = None, exception_handler = None):
  try:
    with timeout(seconds):
      yield
  except TimeoutError:
    if hasattr(timeout_handler, '__call__'):
      timeout_handler(seconds)
    abort("Operation timed out after %d seconds.")
  except Exception, e:
    trace = ''.join(traceback.format_tb(sys.exc_info()[2]))
    if hasattr(exception_handler, '__call__'):
      exception_handler(seconds, e, trace)
    abort("Operation failed: %s\n%s" % (e, trace))
