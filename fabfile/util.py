from contextlib import contextmanager
from functools import wraps
from time import localtime, time, strftime, gmtime
import os, re, socket

from fabric import tasks
from fabric.api import settings, env, hide, local, prompt, abort, run, puts
from fabric.utils import puts
from fabric.colors import green

MAX_NODE_IDX = 50

class local_command(str):
    def __init__(self, _command):
        self._result = None
        if hasattr(_command, '__call__'):
            self._func = _command
            self._command = None
        else:
            self._function = None
            self._command = _command

    def run(self, *args, **kwargs):

        if hasattr(self, '_func') and self._func:
            self._command = self._func(*args, **kwargs)

        if not self._result:
            if env.debugging:
                puts("Running: " + green(self._command))
            self._result = local(self._command, capture=True)
            self._result.code = self._result.return_code
        return self._result

    def code(self):
        return self._result.return_code if self._result else 0

    def stderr(self):
        return self._result.stderr if self._result else ''

    def stdout(self):
        return self._result if self._result else ''

    def failed(self):
        return False if not self._result else self._result.failed

    def succeeded(self):
        return False if not self._result else self._result.succeeded

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def __enter__(self):
        return self.run()

    def __exit__(self, *exc_info):
        pass

    def __str__(self):
        return self.run()

    def __repr__(self):
        return repr(self.run())

class volatile_command(local_command):
    def run(self, *args, **kwargs):

        if hasattr(self, '_func') and self._func:
            self._command = self._func(*args, **kwargs)

        if env.dry_run:
            self._command = "/bin/echo %s" % self._command

        if not self._result:
            if env.debugging:
                puts("Running: " + green(self._command))
            self._result = local(self._command, capture=True)
            self._result.code = self._result.return_code
        return self._result


benchmark_stack = []
def benchmark_label():
    return '.'.join(benchmark_stack)

def benchmark(disable_if=None):
    def _wrap_as_new(original, new):
        if isinstance(original, tasks.Task):
            return tasks.WrappedCallableTask(new)
        return new

    @contextmanager
    def bench(task_name):
        state = 'succeeded'
        indent = '=' * (len(benchmark_stack) * 2)
        try:
            benchmark_stack.append(task_name)
            start_time = time()
            puts("%s====> Task '%s' started at %s" %
                (indent, benchmark_label(), strftime("%a, %d %b %Y %H:%M:%S", localtime(start_time))))
            yield
        except (Exception, SystemExit), e:
            state = 'failed'
            raise e
        finally:
            end_time = time()
            puts("<====%s Task '%s' %s at %s (runtime: %s)" %
                (indent, benchmark_label(), state, strftime("%a, %d %b %Y %H:%M:%S",
                    localtime(end_time)), strftime("%H:%M:%S", gmtime(end_time - start_time))))
            benchmark_stack.pop()

    def real_decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            disabled = disable_if if disable_if and getattr(disable_if, '__call__') else lambda: False
            if disabled() or not env.benchmark:
                puts("not using benchmark for task: ", func.__name__)
                return func(*args, **kwargs)

            result = None
            with bench(func.__name__):
                result = func(*args, **kwargs)
            return result
        return _wrap_as_new(func, inner)

    if hasattr(disable_if, '__name__') and disable_if.__name__ == (lambda: None).__name__:
        # lambdas are functions so we need to first check if disable_if is a lambda
        return real_decorator
    elif type(disable_if) == type(real_decorator):
        # If it's not a lambda, see if it's a function reference so we can allow
        # non-factory-style decorator use (@decorator vs @decorator())
        return real_decorator(disable_if)
    elif type(disable_if) == type('string'):
        # otherwise, if we have a string, we are likely calling it as a contextmanager
        return bench(disable_if)
    else:
        # otherwise, just pass the decorater back as is as we likely have a non-lambda argument
        return real_decorator

def flatten(seq):
    l = []
    for elt in seq:
        t = type(elt)
        if t is tuple or t is list:
            for elt2 in flatten(elt):
                l.append(elt2)
        else:
            l.append(elt)
    return l

def capture(command, warn_only=False):
    '''
    Runs a command on the remote server and returns the non-garbled output
    '''
    with settings(hide('running', 'warnings', 'stdout'), warn_only=warn_only):
        # output can come back with carriage returns but no newlines
        # so convert them to newlines (which is what we typically expect)
        return "\n".join(re.compile(r'(?:\r\n|\r)').split(run(command)))

def runner():
  if 'runner' not in env:
    with settings(hide('running')):
        env.runner = local('whoami', capture=True)
    if env.runner == 'root':
      if 'SUDO_USER' in os.environ:
        env.runner = os.environ['SUDO_USER']
      elif env.interact:
        env.runner = prompt(green('Please enter your name:'), validate=r'[\w\s]+')
      else:
        abort('refusing to run without valid non-root user identity.\nMake sure you use sudo and haven\'t set interact:no')
  return env.runner

def mongo_server_list(prefix='mongo', max_node_index=MAX_NODE_IDX, **kwargs):
    return server_list(prefix, '', max_node_index=max_node_index, **kwargs)

def mysql_server_list(prefix='mysql', max_node_index=MAX_NODE_IDX, **kwargs):
    return server_list(prefix, '', max_node_index=max_node_index, **kwargs)

def web_server_list(prefix='web', max_node_index=MAX_NODE_IDX, **kwargs):
    return server_list(prefix, '', max_node_index=max_node_index, **kwargs)

def php_server_list(prefix='php', max_node_index=MAX_NODE_IDX, **kwargs):
    return server_list(prefix, '', max_node_index=max_node_index, **kwargs)

def server_list(prefix, suffix='', user=None, max_node_index=MAX_NODE_IDX):
    '''
    Get a list of valid php server hostnames by looping over all available prefixed name possibities
    and node index numbers from 1 to MAX_PHP_NODE_IDX, and seeing if A. we can resolve it, and B. if
    we can connect.

    If (A) fails (socket.gaierror), then we know we've reach the number limit for that prefix and can
    stop looking for more hosts with that prefix at higher idx values.

    If (B) fails (socket.timeout), then we assume that the host is not up, or not receiving SSH connections
    currently, so we can skip it.

    If neither (A) nor (B) fail, then we simply add the host to our list as a viable host to connect to.
    '''

    if not user: user = env.user

    if hasattr(prefix, '__iter__'):
        # if we were passed an iterable, use it (e.g., list, tuple)
        prefixes = prefix
    else:
        # otherwise, we only use one type with no suffix
        prefixes = [prefix]
        suffix   = ''

    collection = []

    for prefix in prefixes:
        node_idx = 1
        while node_idx < max_node_index:
            try:
                node_name = "%s%02d%s.%s.lipsum.com" % ( prefix, node_idx, suffix, env.env_short )
                node_idx += 1

                if env.debugging: print "Attempting connection to %s --> " % node_name,
                (family, socktype, proto, garbage, address) = socket.getaddrinfo(node_name, 'ssh')[0]
                s = socket.create_connection(address, 0.15)
                s.close()

                if env.debugging: print "SUCCESS"
                collection.append("%s@%s" % (user, node_name))
            except socket.gaierror:
                # unable to get address info for the specified hostname
                if env.debugging: print "FAILED: Unable to get address for %s" % node_name
                break
            except (socket.timeout, socket.error):
                # either timed out on connect, or connection itself failed
                # in either case, we should skip the host
                if env.debugging: print "FAILED: Timedout or Socket Error on: %s" % node_name
                pass
    return collection

