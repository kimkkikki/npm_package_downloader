import json
import argparse
import os
import shutil
from packaging import version
import requests

parser = argparse.ArgumentParser(
    description='Download PYPI Pakages to disk and upload Nexus OSS')
parser.add_argument('package', metavar='PackageName',
                    type=str, help='PYPI Package name')
parser.add_argument('version', metavar='Version',
                    type=str, help='Package Version')
parser.add_argument('--upload', action="store_true",
                    help='Upload to Nexus OSS')
parser.add_argument('--no_ssl', action="store_true",
                    help='Download From http')

args = parser.parse_args()

verify = True
if args.no_ssl:
    verify = False

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

pypi_download_folder = config['pypi-download-folder']

if not os.path.exists(pypi_download_folder):
    os.mkdir(pypi_download_folder)


def check_version(request, test):
    if request == '*':
        return True
    if version.parse(request) == version.parse(test):
        return True

    return False


def get_package(package_name, package_version):
    package_url = f'https://pypi.org/pypi/{package_name}/json'
    response = requests.get(package_url, verify=verify)
    if response.status_code == 200:
        parsed = json.loads(response.content)
        versions = parsed['releases']
        download_files = []
        download_version = None
        for _version, value in versions.items():
            check_result = check_version(package_version, _version)
            if check_result:
                if download_version is None or version.parse(download_version) < version.parse(_version):
                    download_files = [release_obj['url'] for release_obj in value]
                    download_version = _version

        dependencies = parsed['info']['requires_dist']
        if dependencies is not None:
            for version_string in dependencies:
                if ";" in version_string:
                    continue

                splited_version = version_string.split(' ')
                dep_package_name = splited_version[0]
                if len(splited_version) == 1:
                    dep_version = '*'
                else:
                    dep_version = splited_version[1].replace('>', '').replace('<', '').replace('=', '').replace('(', '').replace(')', '')

                    if dep_version == '':
                        dep_version = '*'
                get_package(dep_package_name, dep_version)

        for download_file in download_files:
            pypi_file_name = download_file.split('/')[-1]
            already_files = os.listdir(pypi_download_folder)
            if pypi_file_name in already_files:
                print(f'{pypi_file_name} is already download skip')
                continue

            r = requests.get(download_file, stream=True, verify=verify)
            if r.status_code == 200:
                with open(f'{pypi_download_folder}/{pypi_file_name}', 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                    print(f'{pypi_file_name} download success')

            if args.upload:
                upload_result = requests.post(f"{config['nexus-host']}/service/rest/v1/components?repository={config['nexus-pypi-repository']}",
                                              auth=requests.auth.HTTPBasicAuth(config['nexus-username'], config['nexus-password']), files={
                                                  'upload_file': open(f'{pypi_download_folder}/{pypi_file_name}', 'rb')
                                              })

                if upload_result.status_code == 204:
                    print(f'{pypi_file_name} nexus upload success')
                else:
                    print(f'{pypi_file_name} nexus upload failure')


get_package(args.package, args.version)
