PyPiGit
=======

A simple PyPi-like server that automatically generates python packages from git tags.

Installation
------------
```bash
pip install pypigit
```

How To
------

* Prepare `repos.yaml`:
```yaml
repositories:
  - https://github.com/<author>/<repo>.git
  - git@github.com:<author>/<repo>.git
```

* Start a server (see `python -m pypigit.server --help` for all arguments):
```bash
python -m pypigit.server --repos="repos.yaml"
```

* Draft a release (that will create certain tag)
* Install a package with pip:
```bash
pip install --extra-index-url http://localhost:9498/simple <repo>==1.0.2
```

It will automatically build a package from tag `1.0.2`, and deliver it to pip. Once
built, it will be stored in `--cache-direcory` so consecutive calls will take no time.

Optionally, you can specify package name in case you have repository name wrong:
```yaml
repositories:
  - url: https://github.com/<author>/company-<repo>.git
    name: <package-name>
  - url: https://github.com/<author>/company-<repo>.git
    name: <package-name>
```

SSH
---

This project is aimed to host private packages, so ssh git remotes are supported:
```yaml
repositories:
  - url: git@github.com:<author>/<repo>.git
    ssh_key: |
      -----BEGIN RSA PRIVATE KEY-----
      <private key>
      -----END RSA PRIVATE KEY-----
```
If you have same private ssh key for all repositories, you can simply define `default_ssh_key` instead:
```yaml
repositories:
  - git@github.com:<author>/<repo>.git
  - git@github.com:<author>/<repo>.git
  - git@github.com:<author>/<repo>.git
default_ssh_key: |
  -----BEGIN RSA PRIVATE KEY-----
  <private key>
  -----END RSA PRIVATE KEY-----
    
```

Developer Use
-------------

Branches with `dev0` in name (for example, `0.1.dev0`) will be treated specially: `pypigit` will automatically
increment a new build version (for example, `0.1.dev1`, `0.1.dev2`, `0.1.dev3` etc) for each commit hash change.

All you have to do is:

```
pip install --extra-index-url http://localhost:9498/simple --upgrade --no-cache-dir "repo-name>=0.1.dev"
```

It will install a new package iteration each time the last commit hash has changed.
Only [PEP440](https://www.python.org/dev/peps/pep-0440/) compliant branch names will be exported.


Note, this can only work if you use module `pypigit_version` in your project to 
version the packages automatically:

```

setup(
    ...
    setup_requires=["pypigit-version"],
    git_version="0.1.0",
    ...
)
```

It will try to obtain a version automatically:
* If the repo's current tag matches PEP440, it will be used
* If the repo's current branch matches PEP440, it will be used
* If `PYPIGIT_VERSION` is defined (for auto-incrementing), it will be used
* Otherwise, it will fallback to the `git_version` value.
