
from . import run_on_executor
import giturlparse
import json
from concurrent.futures import ThreadPoolExecutor
import git
import os
import os.path
import subprocess
import stat
from shutil import copyfile, rmtree
from tempfile import TemporaryDirectory


class CacheRedirectException(Exception):
    def __init__(self, url):
        self.url = url


class GitRepository(object):
    executor = ThreadPoolExecutor()
    g = git.cmd.Git()

    def __init__(self, url, cache_directory, public_url):
        self.repo_url = url
        self.parsed_url = giturlparse.parse(url)
        if not self.parsed_url.valid:
            raise RuntimeError("Repo {0} is not valid".format(url))
        self.cache_directory = os.path.join(cache_directory, self.name())
        self.cache_public_url = public_url + "/cache/" + self.name()
        self.public_url = public_url

    @run_on_executor
    def list_versions(self):
        repo_name = self.name()
        tags = GitRepository.g.ls_remote(self.repo_url, tags=True)
        result = {}
        for line in tags.split('\n'):
            ref_hash, ref = line.split('\t')
            tag_name = ref.split("/")[-1]
            tar_name = self.package_tar(tag_name)
            result[tar_name] = self.public_url + "/download/" + repo_name + "/" + tar_name
        return result

    def get_cache_url(self, package_version):
        return self.cache_public_url + "/" + self.package_tar(package_version)

    def package_tar(self, package_version):
        return "{0}-{1}.tar.gz".format(self.name(), package_version)

    @run_on_executor
    def download(self, package_version):
        repo_name = self.name()
        if not os.path.isdir(self.cache_directory):
            os.mkdir(self.cache_directory)

        cache_url = self.get_cache_url(package_version)
        tar_name = self.package_tar(package_version)
        if os.path.isfile(os.path.join(self.cache_directory, tar_name)):
            return cache_url

        def set_rw(operation, name, exc):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
            return True

        with TemporaryDirectory(prefix="pypigit") as temp_dir:
            r = git.Git(temp_dir)
            r.clone(self.repo_url, branch=package_version, depth=1)
            build = os.path.join(temp_dir, repo_name)
            p = subprocess.Popen("python setup.py sdist", stdout=subprocess.PIPE, shell=True, cwd=build)
            p.communicate()

            copyfile(os.path.join(build, "dist", tar_name), os.path.join(self.cache_directory, tar_name))

            rmtree(build, onerror=set_rw)

        return cache_url

    def name(self):
        return self.parsed_url.repo


class GitRepositories(object):
    def __init__(self, repos_filename, cache_directory, public_url):

        with open(repos_filename, "r") as f:
            repos = json.load(f)

        if not isinstance(repos, dict):
            raise RuntimeError("--repos file should be a json object")

        if "repositories" not in repos:
            raise RuntimeError("No 'repositories' section in --repos file")

        self.repositories = {
            repo.name(): repo
            for repo in map(lambda path: GitRepository(path, cache_directory, public_url),
                            filter(lambda s: isinstance(s, str), repos["repositories"]))
        }

    def find(self, name):
        return self.repositories.get(name)

    def list(self):
        return self.repositories.keys()
