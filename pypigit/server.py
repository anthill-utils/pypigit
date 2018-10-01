
from tornado.web import Application, StaticFileHandler
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line

from . import handler
from . repos import GitRepositories

import os
import logging

define("port", type=int, default="9498", help="Listen port")
define("cache-directory", type=str, default=".pypigit", help="Cache directory")
define("public-url", type=str, default="http://localhost:9498", help="Public URL directory")
define("repos", type=str, help="YAML file with list of git remotes")


class PyPiGITServer(Application):
    def __init__(self, handlers, **settings):
        super().__init__(handlers, **settings)

        if options.repos is None:
            raise RuntimeError("--repos argument is required")

        if not os.path.isdir(options.cache_directory):
            os.mkdir(options.cache_directory)

        self.repos = GitRepositories(options.repos, options.cache_directory, options.public_url)

        logging.info("Serving on {0}".format(options.public_url))


def make_app():
    return PyPiGITServer([
        (r"/simple/?", handler.IndexHandler),
        (r"/simple/([a-zA-Z0-9_-]+)/?", handler.PackageHandler),
        (r"/download/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)-([a-zA-Z0-9_\.-]+)\.tar\.gz", handler.DownloadPackageHandler),
        (r'/cache/(.*)', StaticFileHandler, {'path': options.cache_directory}),
    ])


if __name__ == "__main__":
    parse_command_line()
    app = make_app()
    app.listen(options.port)
    IOLoop.current().start()
