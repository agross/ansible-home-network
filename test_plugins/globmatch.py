from pathlib import PurePosixPath


def globmatch(path, pattern, state):
  """Match a source-relative glob; a trailing slash requires a directory.

  Requires Python 3.13 or newer on the Ansible controller.
  """
  if not path or not pattern:
    return path == pattern

  if pattern.endswith('/'):
    if state != 'directory':
      return False
    pattern = pattern.rstrip('/')

  return PurePosixPath(path).full_match(pattern, case_sensitive=True)


class TestModule(object):
  def tests(self):
    return {
      'globmatch': globmatch
    }
