
from tornado.web import RequestHandler, HTTPError
from . repos import GitRepositoryError, CacheRedirectException

from xmlrpc.client import loads as rpc_loads
from xmlrpc.client import dumps as rpc_dumps


class IndexHandler(RequestHandler):
    def get(self):
        self.render("templates/simple_index.html", repositories=self.application.repos.list())

    async def call_search(self, specs, operator='or'):
        packages = []

        if "name" in specs:
            name_to_search = specs["name"][0]
            repo = self.application.repos.find(name_to_search)
            if repo is not None:
                try:
                    versions = await repo.list_versions(True)
                except GitRepositoryError as e:
                    pass
                else:
                    ordering = 0
                    for version in versions:
                        packages.append({
                            "_pypi_ordering": ordering,
                            "name": name_to_search,
                            "version": version,
                            "summary": version
                        })
                        ordering += 1

        return packages,

    async def post(self):
        try:
            params, method_name = rpc_loads(self.request.body.decode())
        except (KeyError, ValueError):
            raise HTTPError(400, "Bad XML")

        method = getattr(self, "call_{0}".format(method_name), None)

        if method is None:
            raise HTTPError(400, "No such method")

        try:
            result = await method(*params)
        except Exception as e:
            raise HTTPError(400, str(e))
        else:
            self.write(rpc_dumps(result, method_name, methodresponse=True))


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
