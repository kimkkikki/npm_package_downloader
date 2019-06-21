# Package downloader for Nexus OSS

If your nexus oss does not have direct access to the npm / pypi registry, it is a script that runs npm / pypi repository and server both on the connectable machine and manually raises the npm / pypi package.

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# NPM Example
python download_from_npm.py --help
python download_from_npm.py forever 1.0.0 --dev --upload

# PYPI Example
python download_from_pypi.py --help
python download_from_pypi.py flask * --upload

# Maven Example
python download_from_maven.py --help
python download_from_maven.py org.apache.spark spark-core_2.12 2.4.3 --upload --no_ssl
```
