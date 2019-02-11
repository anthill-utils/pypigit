from . import run_on_executor, PrivateSSHKeyContext

import giturlparse
from concurrent.futures import ThreadPoolExecutor
from subprocess import run, PIPE
import git
import os
import os.path
import stat
import yaml
import re
import json
import logging
import sys

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
    version_validator = re.compile(r"^(\d+!)?(\d+)(\.\d+)+([\.\_\-])?(\.?dev\d*)?$")

    def __init__(self, settings, cache_directory, public_url, default_private_key=None):

        if isinstance(settings, str):
            url = settings
            name = None
            self.private_key = None
        elif isinstance(settings, dict):
            url = settings.get("url", None)
            if url is None:
                raise RuntimeError("Repo is an object but has no `url` property")
            name = settings.get("name", None)
            self.private_key = settings.get("ssh_key", default_private_key)
        else:
            raise RuntimeError("Repo should be a string or a object")

        self.repo_url = url
        self.parsed_url = giturlparse.parse(url)
        if not self.parsed_url.valid:
            raise RuntimeError("Repo {0} is not valid".format(url))
        self._name = name or self.parsed_url.repo
        self.cache_directory = os.path.join(cache_directory, self.name())
        self.cache_public_url = public_url + "/cache/" + self.name()
        self.public_url = public_url

    @run_on_executor
    def list_versions(self, just_versions=False):
        repo_name = self.name()
        with PrivateSSHKeyContext(ssh_private_key=self.private_key) as ssh_private_key_filename:
            g = git.cmd.Git()
            with git_ssh_environment(g, ssh_private_key_filename=ssh_private_key_filename):
                try:
                    tags = g.ls_remote(self.repo_url)
                except git.GitCommandError as e:
                    raise GitRepositoryError(500, "Failed to fetch remote repository: {0}".format(e.status))
                result = [] if just_versions else {}
                skipped = []
                for line in tags.split('\n'):
                    ref_hash, ref = line.split('\t')
                    ref_split = ref.split("/")
                    if len(ref_split) != 3:
                        continue
                    refs, kind, name = ref_split

                    version_info = re.match(GitRepository.version_validator, name)
                    if not version_info:
                        if name not in ["master", "HEAD"]:
                            skipped.append(name)
                        continue

                    if kind == "heads":
                        postfix = version_info.group(5)
                        # if there's a branch that match PEP440 and dev, auto-generate number
                        if postfix and postfix == "dev0":
                            if not os.path.isdir(self.cache_directory):
                                os.mkdir(self.cache_directory)

                            cache_file = os.path.join(self.cache_directory, ".hashes")
                            if os.path.isfile(cache_file):
                                with open(cache_file, "r") as f:
                                    cache_data = json.load(f)

                            else:
                                cache_data = {}

                            branch_cache = cache_data.get(name, None)
                            if branch_cache is None:
                                branch_cache = {}
                                cache_data[name] = branch_cache

                            last_version = branch_cache.get("v", 0)
                            last_hash = branch_cache.get("h", None)

                            if last_hash == ref_hash:
                                new_version = last_version
                            else:
                                new_version = last_version + 1
                                branch_cache["v"] = new_version
                                branch_cache["h"] = ref_hash
                                with open(cache_file, "w") as f:
                                    json.dump(cache_data, f)

                            name = (version_info.group(1) or '') + (version_info.group(2) or '') + \
                                   (version_info.group(3) or '') + (version_info.group(4) or '') + "dev" + \
                                   str(new_version)

                    tar_name = self.package_tar(name)

                    if just_versions:
                        result.append(name)
                    else:
                        result[tar_name] = self.public_url + "/download/" + repo_name + "/" + tar_name
                if skipped:
                    logging.warning("{0} skipped versions, because they do not comply PEP440: {1}".format(
                        repo_name, ", ".join(skipped)
                    ))
                return result

    def get_cache_url(self, package_version):
        return self.cache_public_url + "/" + self.package_tar(package_version)

    def package_tar(self, package_version):
        return "{0}-{1}.tar.gz".format(self.name(), package_version)

    @run_on_executor
    def download(self, package_version):
        cache = True
        version_info = re.match(GitRepository.version_validator, package_version)
        original_version = package_version
        if version_info:
            postfix = version_info.group(5)
            if postfix and postfix.startswith("dev"):
                original_version = package_version
                package_version = (version_info.group(1) or '') + (version_info.group(2) or '') + \
                                  (version_info.group(3) or '') + (version_info.group(4) or '') + "dev0"
                cache = False

        repo_name = self.parsed_url.repo
        package_name = self.name()
        tar_name = self.package_tar(original_version)

        if cache:
            if not os.path.isdir(self.cache_directory):
                os.mkdir(self.cache_directory)

            cache_url = self.get_cache_url(package_version)
            if os.path.isfile(os.path.join(self.cache_directory, tar_name)):
                return cache_url
        else:
            cache_url = None

        # noinspection PyUnusedLocal
        def set_rw(operation, name, exc):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
            return True

        with TemporaryDirectory(prefix="pypigit") as temp_dir:
            g = git.Git(temp_dir)

            try:
                with PrivateSSHKeyContext(ssh_private_key=self.private_key) as ssh_private_key_filename:
                    with git_ssh_environment(g, ssh_private_key_filename=ssh_private_key_filename):
                        g.clone(self.repo_url, package_name, branch=package_version, depth=1)

                build = os.path.join(temp_dir, package_name)

                env = os.environ.copy()
                env["PYPIGIT_VERSION"] = original_version

                p = run("{0} setup.py --version".format(sys.executable), stdout=PIPE, shell=True, cwd=build, env=env)

                if p.returncode != 0:
                    raise GitRepositoryError(400, "Package {0} of {1} has failed to provide version".format(
                        package_name, original_version
                    ))

                py_version = p.stdout.decode().splitlines()[-1]
                if py_version != original_version:
                    raise GitRepositoryError(400, "Package {0} of tag {1} contains version {2} instead".format(
                        package_name, package_version, py_version
                    ))

                p = run("{0} setup.py sdist".format(sys.executable), stdout=PIPE, shell=True, cwd=build, env=env)

                if p.returncode != 0:
                    raise GitRepositoryError(400, "Package {0} of {1} build has failed with error code {2}".format(
                        package_name, original_version, p.returncode
                    ))

                if not os.path.isfile(os.path.join(build, "dist", tar_name)):
                    raise GitRepositoryError(400, "Package {0} of version {1} did not produce dist {2}".format(
                        package_name, original_version, tar_name
                    ))

                if cache:
                    copyfile(os.path.join(build, "dist", tar_name), os.path.join(self.cache_directory, tar_name))
                else:
                    with open(os.path.join(build, "dist", tar_name), 'rb') as f:
                        return f.read()

            finally:
                # noinspection PyTypeChecker
                rmtree(build, onerror=set_rw)

        if cache:
            raise CacheRedirectException(cache_url)

    def name(self):
        return self._name


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
