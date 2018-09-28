
from . import run_on_executor, PrivateSSHKeyContext

import giturlparse
from concurrent.futures import ThreadPoolExecutor
import git
import os
import os.path
import subprocess
import stat
import yaml

from shutil import copyfile, rmtree
from tempfile import TemporaryDirectory


def git_ssh_command(private_key):
    return "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {0}".format(private_key)


def git_ssh_environment(g, ssh_private_key_filename=None):
    if ssh_private_key_filename:
        return g.custom_environment(GIT_SSH_COMMAND=git_ssh_command(ssh_private_key_filename))
    return g.custom_environment()


class CacheRedirectException(Exception):
    def __init__(self, url):
        self.url = url


class GitRepositoryError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class GitRepository(object):
    executor = ThreadPoolExecutor()

    def __init__(self, settings, cache_directory, public_url, default_private_key=None):

        if isinstance(settings, str):
            url = settings
            self.private_key = None
        elif isinstance(settings, dict):
            url = settings.get("url", None)
            if url is None:
                raise RuntimeError("Repo is an object but has no `url` property")
            self.private_key = settings.get("ssh_key", default_private_key)
        else:
            raise RuntimeError("Repo should be a string or a object")

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
        with PrivateSSHKeyContext(ssh_private_key=self.private_key) as ssh_private_key_filename:
            g = git.cmd.Git()
            with git_ssh_environment(g, ssh_private_key_filename=ssh_private_key_filename):
                try:
                    tags = g.ls_remote(self.repo_url, tags=True)
                except git.GitCommandError as e:
                    raise GitRepositoryError(500, "Failed to fetch remote repository: {0}".format(e.status))
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

        # noinspection PyUnusedLocal
        def set_rw(operation, name, exc):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
            return True

        with TemporaryDirectory(prefix="pypigit") as temp_dir:
            g = git.Git(temp_dir)

            with PrivateSSHKeyContext(ssh_private_key=self.private_key) as ssh_private_key_filename:
                with git_ssh_environment(g, ssh_private_key_filename=ssh_private_key_filename):
                    g.clone(self.repo_url, branch=package_version, depth=1)

            build = os.path.join(temp_dir, repo_name)
            p = subprocess.Popen("python setup.py sdist", stdout=subprocess.PIPE, shell=True, cwd=build)
            p.communicate()

            copyfile(os.path.join(build, "dist", tar_name), os.path.join(self.cache_directory, tar_name))

            # noinspection PyTypeChecker
            rmtree(build, onerror=set_rw)

        return cache_url

    def name(self):
        return self.parsed_url.repo


class GitRepositories(object):
    def __init__(self, repos_filename, cache_directory, public_url):

        with open(repos_filename, "r") as f:
            repos = yaml.load(f)

        if not isinstance(repos, dict):
            raise RuntimeError("--repos file should be a json object")

        default_private_key = repos.get("default_ssh_key")

        if "repositories" not in repos:
            raise RuntimeError("No 'repositories' section in --repos file")

        self.repositories = {
            repo.name(): repo
            for repo in map(
                lambda settings: GitRepository(
                    settings, cache_directory, public_url, default_private_key=default_private_key
                ), repos["repositories"]
            )
        }

    def find(self, name):
        return self.repositories.get(name)

    def list(self):
        return self.repositories.keys()
