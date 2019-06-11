import requests
import argparse
import json
import shutil
import os


parser = argparse.ArgumentParser(
    description='Download NPM Pakages to disk and upload Nexus OSS')
parser.add_argument('package', metavar='PackageName',
                    type=str, help='NPM Package name')
parser.add_argument('version', metavar='Version',
                    type=str, help='Package Version')
parser.add_argument('--dev', action="store_true",
                    help='Include Dev dependencies')
parser.add_argument('--upload', action="store_true",
                    help='Upload to Nexus OSS')
parser.add_argument('--no_ssl', action="store_true",
                    help='Download From http')

args = parser.parse_args()

input_package = args.package
input_version = args.version

packages = set()
notFound = set()


with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

npm_download_folder = config['npm-download-folder']

if not os.path.exists(npm_download_folder):
    os.mkdir(npm_download_folder)


def check_version(request_version, test_version):
    request_version = request_version.split('-')[0]
    test_version = test_version.split('-')[0]
    middle_free = False
    miner_free = False
    if '>' in request_version or '*' in request_version:
        return True
    if '^' in request_version:
        request_version = request_version.replace('^', '')
        if request_version.split('.')[0] == '0':
            miner_free = True
        else:
            middle_free = True
    if '~' in request_version:
        miner_free = True
        request_version = request_version.replace('~', '')

    if 'x' in request_version:
        for index, x in enumerate(request_version.split('.')):
            if x == 'x':
                if index == 1:
                    middle_free = True
                elif index == 2:
                    miner_free = True
                break

        request_version = request_version.replace('x', '0')

    splited_request_version = request_version.split('.')
    splited_test_version = test_version.split('.')

    if len(splited_request_version) == 1:
        middle_free = True
        splited_request_version.append('0')
        splited_request_version.append('0')
    elif len(splited_request_version) == 2:
        miner_free = True
        splited_request_version.append('0')

    request_1 = splited_request_version[0]
    request_2 = splited_request_version[1]
    request_3 = splited_request_version[2]
    test_1 = splited_test_version[0]
    test_2 = splited_test_version[1]
    test_3 = splited_test_version[2]
    if request_1 == test_1:
        if middle_free:
            if int(request_2) <= int(test_2):
                return True
        elif request_2 == test_2:
            if miner_free:
                if int(request_3) <= int(test_3):
                    return True
            else:
                if request_3 == test_3:
                    return True

    return False


def get_package(package_name, package_version):
    package_url = 'https://registry.npmjs.org/{}'.format(package_name)
    if args.no_ssl:
        package_url = package_url.replace('https', 'http')
    response = requests.get(package_url)
    if response.status_code == 200:
        parsed = json.loads(response.content)
        if 'versions' not in parsed:
            return
        versions = parsed['versions']
        tarball = None
        download_version = None
        dependencies = {}
        devDependencies = {}
        for version, value in versions.items():
            check_result = check_version(package_version, version)
            if check_result:
                tarball = value['dist']['tarball']
                download_version = version
                if 'dependencies' in value:
                    dependencies = value['dependencies']
                if 'devDependencies' in value:
                    devDependencies = value['devDependencies']

        package = '{}@{}'.format(package_name, download_version)
        if package in packages:
            return
        # print(package)

        packages.add(package)

        for dep_package, dep_version in dependencies.items():
            get_package(dep_package, dep_version)

        if args.dev:
            for dep_package, dep_version in devDependencies.items():
                get_package(dep_package, dep_version)

        if tarball is None:
            print('{} tarball not found'.format(package))
            return

        if args.no_ssl:
            tarball = tarball.replace('https', 'http')

        npm_file_name = tarball.split('/')[-1]
        already_files = os.listdir(npm_download_folder)
        if npm_file_name in already_files:
            print('{} is already download skip'.format(npm_file_name))
            return

        r = requests.get(tarball, stream=True)
        if r.status_code == 200:
            with open('{}/{}'.format(npm_download_folder, npm_file_name), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                print('{} download success'.format(npm_file_name))

        if args.upload:
            upload_result = requests.post('{}/service/rest/v1/components?repository={}'.format(config['nexus-host'], config['nexus-npm-repository']),
                                          auth=requests.auth.HTTPBasicAuth(config['nexus-username'], config['nexus-password']), files={
                'upload_file': open('{}/{}'.format(npm_download_folder, npm_file_name), 'rb')
            })

            if upload_result.status_code == 204:
                print('{} nexus upload success'.format(npm_file_name))
            else:
                print('{} nexus upload failure'.format(npm_file_name))
    else:
        notFound.add(package_name + package_version)


get_package(input_package, input_version)
if len(notFound) > 0:
    print('{} packages not found'.format(notFound))
