PyPiGit
=======

A simple PyPi-like server that automatically generates python packages from git tags.

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