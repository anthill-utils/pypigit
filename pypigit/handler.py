
from tornado.web import RequestHandler, HTTPError


class MainHandler(RequestHandler):
    def get(self):
        self.write("hello")


class IndexHandler(RequestHandler):
    def get(self):
        self.render("templates/simple_index.html", repositories=self.application.repos.list())


class PackageHandler(RequestHandler):
    async def get(self, package_name):

        repo = self.application.repos.find(package_name)

        if repo is None:
            raise HTTPError(404, "No such package")

        versions = await repo.list_versions()

        self.render("templates/package_versions.html", package_name=package_name, versions=versions)


class DownloadPackageHandler(RequestHandler):
    async def get(self, package_name, ignored, package_version):

        repo = self.application.repos.find(package_name)

        if repo is None:
            raise HTTPError(404, "No such package")

        self.redirect(await repo.download(package_version))
