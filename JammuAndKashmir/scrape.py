import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

main_url = 'https://rgp.jk.gov.in/gazette.html'
main_url_base = 'https://rgp.jk.gov.in/'

def process_section(session, section):
    name = section[0]
    print(f'processing section {name}')
    rel_url = section[1]
    fname = name.replace(' ', '_') + '.json'
    file = Path('data') / fname
    if file.exists():
        infos = json.loads(file.read_text())
        return infos

    full_url = main_url_base + rel_url
    resp = session.get(full_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {full_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find('div', {'id': 'MainText-right'})
    a_s = div.find_all('a')
    infos = []
    for a in a_s:
        desc = a.text.strip()
        rel_url = a.attrs['href']
        url = main_url_base + rel_url
        info = { 'desc': desc, 'url': url }
        infos.append(info)
    file.write_text(json.dumps(infos))
    return infos
        

def clean_name(name):
    for c in [' ', '\t', '\n', '\r', '.', ',', '\xa0']:
        name = name.replace(c, '_')
    parts = name.split('_')
    parts = [ p for p in parts if p != '' ]
    name = '_'.join(parts)
    return name
    

def download_gazette(session, info):
    name = clean_name(info['desc'])
    fname = name + '.pdf'
    gaz_dir = Path('data') / 'gazettes'
    gaz_dir.mkdir(exist_ok=True, parents=True)
    gaz_file = gaz_dir / fname
    if gaz_file.exists():
        return
    url = info['url']
    print(f'downloading {url}')
    resp = session.get(url)
    if not resp.ok:
        raise Exception(f'unable to get file from {url}')
    gaz_file.write_bytes(resp.content)


if __name__ == '__main__':
    Path('data').mkdir(exist_ok=True) 
    session = requests.session()
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {main_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find('div', {'id': 'MainText'})
    links = div.find_all('a')
    sections = [(link.text.strip(), link.attrs['href']) for link in links]
    infos = []
    for section in sections:
        infos += process_section(session, section)
    for info in infos:
        download_gazette(session, info)
