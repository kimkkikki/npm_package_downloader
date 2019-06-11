# Package downloader for Nexus OSS

If your nexus oss does not have direct access to the npm / pypi registry, it is a script that runs npm / pypi repository and server both on the connectable machine and manually raises the npm / pypi package.

```
pipenv install

# Example
python download_from_npm.py forever 1.0.0 --dev --upload

# Example
python download_from_pypi.py flask * --upload
```
