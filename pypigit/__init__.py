
from tornado.ioloop import IOLoop


def run_on_executor(method):
    def wrapper(self, *args):
        executor = getattr(self, "executor")
        return IOLoop.current().run_in_executor(executor, method, self, *args)
    return wrapper

