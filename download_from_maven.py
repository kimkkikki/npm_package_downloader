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


circular_ref = set()


def get_package(group_id: str, artifact_id: str, req_version: str):
    package_url = f"{base_url}{group_id.replace('.', '/')}/{artifact_id}/{req_version}/{artifact_id}-{req_version}"

    jar_file_name = f"{package_url.split('/')[-1]}.jar"
    already_files = os.listdir(maven_download_folder)
    if jar_file_name in already_files:
        print(f'{jar_file_name} is already download skip')
        return

    response = requests.get(f'{package_url}.pom')
    if response.status_code == 200:
        namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}

        et = ElementTree.fromstring(
            response.content.decode().replace('\r', '').replace('\n', ''))
        for dependency in et.findall('.//xmlns:dependency', namespaces):
            _artifactId = dependency.find("xmlns:artifactId", namespaces=namespaces)
            _version = dependency.find("xmlns:version", namespaces=namespaces)
            _groupId = dependency.find("xmlns:groupId", namespaces=namespaces)
            if _artifactId is not None and _version is not None and _groupId is not None:
                if (_groupId.text, _artifactId.text, _version.text) not in circular_ref:
                    circular_ref.add((_groupId.text, _artifactId.text, _version.text))
                    get_package(_groupId.text, _artifactId.text, _version.text)

        r = requests.get(f'{package_url}.jar', stream=True)
        if r.status_code == 200:
            with open(f'{maven_download_folder}/{jar_file_name}', 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                print(f'{jar_file_name} download success')

            if args.upload:
                upload_result = requests.post(f"{config['nexus-host']}/service/rest/v1/components?repository={config['nexus-maven-repository']}",
                                              auth=requests.auth.HTTPBasicAuth(config['nexus-username'], config['nexus-password']), data={
                                                  'groupId': group_id,
                                                  'artifactId': artifact_id,
                                                  'version': req_version,
                                                  'maven2.asset1.extension': 'jar',

                                              }, files={
                                                  'maven2.asset1': open(f'{maven_download_folder}/{jar_file_name}', 'rb'),
                                              })

                if upload_result.status_code == 204:
                    print(f'{jar_file_name} nexus upload success')
                else:
                    print(f'{jar_file_name} nexus upload failure')
                    print(upload_result.content)
        else:
            print(f'{jar_file_name} file download failed, reason : {r}')


get_package(args.groupId, args.artifactId, args.version)
