from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import argparse
import requests
import json
import shutil
import os

parser = argparse.ArgumentParser(
    description='Download YUM Pakages to disk and upload Nexus OSS')
parser.add_argument('package', metavar='PackageName',
                    type=str, help='YUM Package name')
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


selected_repo = None
circular_ref = set()
download_folder = config['yum-download-folder']


def download(package_url):
    file_name = package_url.split('/')[-1]
    already_files = os.listdir(download_folder)
    if file_name in already_files:
        print(f'{file_name} is already download skip')

    r = requests.get(package_url, stream=True, verify=verify)
    if r.status_code == 200:
        with open(f'{download_folder}/{file_name}', 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
            print(f'{file_name} download success')

        if args.upload:
            upload_result = requests.post(f"{config['nexus-host']}/service/rest/v1/components?repository={config['nexus-yum-repository']}",
                                          auth=requests.auth.HTTPBasicAuth(config['nexus-username'], config['nexus-password']), data={
                                              'yum.directory': file_name[0],
                                              'yum.asset.filename': file_name
                                          }, files={
                                              'yum.asset': open(f'{download_folder}/{file_name}', 'rb'),
                                          })

            if upload_result.status_code == 204:
                print(f'{file_name} nexus upload success')
            else:
                print(f'{file_name} nexus upload failure')
                print(upload_result.content)
    else:
        print(f'{file_name} file download failed, reason : {r}')


def get_package(url: str):
    response = requests.get(url, verify=verify)
    package_soup = BeautifulSoup(response.content, 'html.parser')

    has_requires = False
    for h2 in package_soup.find_all('h2'):
        if 'Requires' in h2:
            has_requires = True

    if has_requires:
        requires = []
        for a in package_soup.find_all('tbody')[2].find_all('tr'):
            need = True if a.find('td', {'class': 'mono'}).text != '-' else False
            if need:
                href = a.find(href=True)['href']
                requires.append(href)

        # requires = [a['href'] for a in package_soup.find_all('tbody')[2].find_all(href=True)]
        for require in requires:
            select_package(require.split('/')[-1])

    downloads = [a['href'] for a in package_soup.find_all('tbody')[-3].find_all(href=True)]
    if len(downloads) > 0:
        download(downloads[0])


def select_package(package_name):
    global selected_repo
    if package_name in circular_ref:
        return
    else:
        circular_ref.add(package_name)
        print(f'try {package_name}')

    with urllib.request.urlopen(f'https://pkgs.org/download/{package_name}') as res:
        html = res.read()
        soup = BeautifulSoup(html, 'html.parser')
        centos = soup.find('div', {'id': 'distro-159'})
        links = [a['href'] for a in centos.find_all(href=True)]

        if len(links) > 1:
            if selected_repo is None:
                for i, link in enumerate(links):
                    print(f'{link}를 다운로들 하시려면 {i} 를 입력하세요')

                index = input('다운로드 받을 package를 입력하세요: ')
                selected_repo = links[int(index)].split('/')[-2]
                get_package(links[int(index)])
            else:
                for i, link in enumerate(links):
                    if selected_repo in link:
                        get_package(links[int(i)])

        elif len(links) == 1:
            if selected_repo is None:
                selected_repo = links[0].split('/')[-2]
            get_package(links[0])
        else:
            print(f'{package_name}는 찾을 수 없습니다.')


select_package(args.package)
