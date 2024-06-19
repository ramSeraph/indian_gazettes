import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

main_url = 'https://lakshadweep.gov.in/document-category/gazatte-notifications/'

def get_page_count(session):
    print(f'pulling page count from {main_url}')
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {main_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find('main')
    pagination_div = main.find('div', {'class': 'pegination'})
    lis = pagination_div.find_all('li', {'class': ''})
    if len(lis) == 0:
        return 1
    last_li = lis[-1]
    last_link = last_li.find('a').attrs['href'] 
    last_page_id = int(last_link.split('/')[-1])
    return last_page_id

def get_per_page_infos(session, pno):
    page_dir = Path('data/pages/')
    page_dir.mkdir(exist_ok=True)
    page_file = page_dir / f'{pno}.json'
    if page_file.exists():
        return json.loads(page_file.read_text())
    page_url = main_url + f'page/{pno}'
    print(f'pulling info from {page_url}')
    resp = session.get(page_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {page_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find('main')
    div = main.find('div', {'class': 'distTableContent'})
    table = div.find('table')
    tbody = table.find('tbody')
    trs = tbody.find_all('tr', recursive=False)
    infos = []
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        name = tds[0].text.strip()
        date = tds[1].text.strip()
        url = tds[2].find('a').attrs['href']
        info = { 'name': name, 'date': date, 'url': url }
        infos.append(info)
    page_file.write_text(json.dumps(infos))
    return infos


def get_infos(session):
    page_count = get_page_count(session)
    infos = []
    for i in range(1, page_count + 1):
        infos += get_per_page_infos(session, i)
    return infos

def download_gazette(session, info):
    gaz_dir = Path('data/gazettes')
    gaz_dir.mkdir(exist_ok=True)
    url = info['url']
    parts = url.split('/')
    idx = parts.index('uploads')
    fname = '_'.join(parts[idx+1:])
    file = gaz_dir / fname
    if file.exists():
        return
    print(f'downloading file from {url}')
    resp = session.get(url)
    if not resp.ok:
        raise Exception(f'unable to retrieve file at {url}')
    file.write_bytes(resp.content)


if __name__ == '__main__':
    Path('data').mkdir(exist_ok=True)
    session = requests.session()
    infos = get_infos(session)
    for info in infos:
        download_gazette(session, info)

