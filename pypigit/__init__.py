
from tornado.ioloop import IOLoop
from tempfile import mkstemp
import os


def run_on_executor(method):
    def wrapper(self, *args):
        executor = getattr(self, "executor")
        return IOLoop.current().run_in_executor(executor, method, self, *args)
    return wrapper


class PrivateSSHKeyContext(object):
    """
    This context manager class creates temporary file with ssh_private_key in it,
        and conveniently returns path to it, taking care to remove the file afterwards:

    with PrivateSSHKeyWrapper("private ssh key string") as key_path:
        use key_path here for ssh operations

    key_path deleted afterwards

    """

    def __init__(self, ssh_private_key=None):
        self.name = None
        self.ssh_private_key = ssh_private_key
        self.sys_fd = None

    @staticmethod
    def convert_path(path):
        separator = os.path.sep
        if separator != '/':
            path = path.replace(os.path.sep, '/')
        return path

    def __enter__(self):
        if self.ssh_private_key is None:
            return None

        self.sys_fd, self.name = mkstemp()

        with os.fdopen(self.sys_fd, 'w') as f:
            f.write(self.ssh_private_key)
            f.write("\n")

        return PrivateSSHKeyContext.convert_path(self.name)

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.name is None:
            return

        try:
            os.close(self.sys_fd)
            os.remove(self.name)
        except IOError:
            pass
