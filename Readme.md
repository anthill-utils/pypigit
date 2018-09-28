PyPiGit
=======

A simple PyPi-like server that uses git repositories as a source of python packages.

How To
------

* Prepare `repos.json`:
```json
{
    "repositories": [
        "https://github.com/<author>/<repo>.git",
        "git@github.com:<author>/<repo>.git"
    ]
}
```

* Start a server:
```bash
python -m pypigit.server --repos="repos.json"
```

* Draft a release (that will create certain tag)
```bash
pip install --extra-index-url http://localhost:9498/simple <repo>==1.0.2
```

It will automatically clone tag `1.0.2`, build a `sdist` and cache it.