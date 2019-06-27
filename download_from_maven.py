import json
import argparse
import os
import shutil
import requests
from xml.etree import ElementTree

parser = argparse.ArgumentParser(
    description='Download Maven Pakages to disk and upload Nexus OSS')
parser.add_argument('groupId', metavar='Group ID',
                    type=str, help='Maven jar group ID')
parser.add_argument('artifactId', metavar='Artifact ID',
                    type=str, help='Maven jar artifact ID')
parser.add_argument('version', metavar='Version',
                    type=str, help='Maven jar version')
parser.add_argument('--upload', action="store_true",
                    help='Upload to Nexus OSS')
parser.add_argument('--no_ssl', action="store_true",
                    help='Download From http')

args = parser.parse_args()

base_url = 'https://repo1.maven.org/maven2/'
if args.no_ssl:
    base_url = base_url.replace('https', 'http')

with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

maven_download_folder = config['maven-download-folder']

if not os.path.exists(maven_download_folder):
    os.mkdir(maven_download_folder)


def get_package(group_id: str, artifact_id: str, req_version: str):
    package_url = '{0}{1}/{2}/{3}/{2}-{3}'.format(base_url,
                                                  group_id.replace('.', '/'), artifact_id, req_version)

    jar_file_name = '{}.jar'.format(package_url.split('/')[-1])
    already_files = os.listdir(maven_download_folder)
    if jar_file_name in already_files:
        print('{} is already download skip'.format(jar_file_name))
        return

    response = requests.get('{}.pom'.format(package_url))
    if response.status_code == 200:
        namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}

        et = ElementTree.fromstring(
            response.content.decode().replace('\r', '').replace('\n', ''))
        for dependency in et.findall('.//xmlns:dependency', namespaces):
            _artifactId = dependency.find(
                "xmlns:artifactId", namespaces=namespaces)
            _version = dependency.find(
                "xmlns:version", namespaces=namespaces)
            _groupId = dependency.find(
                "xmlns:groupId", namespaces=namespaces)
            if _artifactId is not None and _version is not None and _groupId is not None:
                get_package(_groupId.text, _artifactId.text, _version.text)

        r = requests.get('{}.jar'.format(package_url), stream=True)
        if r.status_code == 200:
            with open('{}/{}'.format(maven_download_folder, jar_file_name), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                print('{} download success'.format(jar_file_name))

            if args.upload:
                upload_result = requests.post('{}/service/rest/v1/components?repository={}'.format(config['nexus-host'], config['nexus-maven-repository']),
                                              auth=requests.auth.HTTPBasicAuth(config['nexus-username'], config['nexus-password']), data={
                    'groupId': group_id,
                    'artifactId': artifact_id,
                    'version': req_version,
                    'maven2.asset1.extension': 'jar',

                }, files={
                    'maven2.asset1': open('{}/{}'.format(maven_download_folder, jar_file_name), 'rb'),
                })

                if upload_result.status_code == 204:
                    print('{} nexus upload success'.format(jar_file_name))
                else:
                    print('{} nexus upload failure'.format(jar_file_name))
                    print(upload_result.content)
        else:
            print('{} file download failed, reason : {}'.format(jar_file_name, r))


get_package(args.groupId, args.artifactId, args.version)
