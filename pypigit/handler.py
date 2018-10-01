
from tornado.web import RequestHandler, HTTPError
from . repos import GitRepositoryError, CacheRedirectException


class IndexHandler(RequestHandler):
    def get(self):
        self.render("templates/simple_index.html", repositories=self.application.repos.list())


class PackageHandler(RequestHandler):
    async def get(self, package_name):

        repo = self.application.repos.find(package_name)

        if repo is None:
            raise HTTPError(404, "No such package")

        try:
            versions = await repo.list_versions()
        except GitRepositoryError as e:
            raise HTTPError(e.code, e.message)

        self.render("templates/package_versions.html", package_name=package_name, versions=versions)


class DownloadPackageHandler(RequestHandler):
    async def get(self, package_name, ignored, package_version):

        repo = self.application.repos.find(package_name)

        if repo is None:
            raise HTTPError(404, "No such package")

        try:
            package = await repo.download(package_version)
        except CacheRedirectException as e:
            self.redirect(e.url)
        except GitRepositoryError as e:
            raise HTTPError(e.code, e.message)
        else:
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition',
                            'attachment; filename={0}-{1}.tar.gz'.format(package_name, package_version))
            self.write(package)
            self.finish()
