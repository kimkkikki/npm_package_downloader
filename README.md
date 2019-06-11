# NPM Package downloader

If your nexus oss does not have direct access to the npm registry, it is a script that runs npm repository and server both on the connectable machine and manually raises the npm package.

```
pipenv install

# Example
python download_from_npm.py forever 1.0.0 --dev --upload
```
