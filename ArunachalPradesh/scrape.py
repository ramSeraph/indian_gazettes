import json
from pathlib import Path
from pprint import pprint

import requests
from bs4 import BeautifulSoup

base_url = 'https://printing.arunachal.gov.in'
normal_gazette_url = base_url + '/normal_gazette/'
extraordinary_gazette_url = base_url + '/extra_ordinary_gazette/'

def extract_from_url(session, url):
    infos = []
    next_url = None
    print(f'processing url: {url}')
    resp = session.get(url, verify=False)
    if not resp.ok:
        raise Exception(f'unable to retrieve page {url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    div = body.find('div', {'class': 'container'}, recursive=False)
    forms = div.find_all('form')
    for form in forms:
        info = {} 
        inputs = form.find_all('input')
        for inp in inputs:
            k = inp.attrs['name']
            v = inp.attrs['value']
            info[k] = v
        span = form.find('span')
        other = span.text.strip()
        info['other'] = other
        a = form.find('a')
        info['name'] = a.text.strip()
        infos.append(info)
    ul = div.find('ul', {'class': 'pagination'})
    lis = ul.find_all('li')
    if len(lis) != 0:
        next_li = lis[-1]
        next_a = next_li.find('a')
        if next_a.text.strip() == 'Next':
            next_url = next_a.attrs['href']
    return infos, next_url

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'printing.arunachal.gov.in',
    'Origin': base_url,
    'Pragma': 'no-cache',
    'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}
   
def download_gazette(session, info, ref_url):
    full_filename = info['filename']
    fname = full_filename.split('/')[-1]
    gaz_dir = Path('data/gazettes') 
    gaz_dir.mkdir(exist_ok=True, parents=True)
    file = gaz_dir / fname
    if file.exists():
        return
    post_data = {
        'csrfmiddlewaretoken': info['csrfmiddlewaretoken'],
        'filename': full_filename
    }
    post_headers = {}
    post_headers.update(headers)
    post_headers['Referer'] = ref_url
    download_url = base_url + '/download/'

    resp = session.post(download_url, data=post_data, headers=post_headers, verify=False)
    if not resp.ok:
        print(resp.text)
        raise Exception(f'unable to download file {full_filename}')
    file.write_bytes(resp.content)


 
def process_section(session, url, fname):
    file = Path(f'data/{fname}')
    all_infos = []
    infos, next_url = extract_from_url(session, url)
    for info in infos:
        download_gazette(session, info, url)
    all_infos += infos
    while True:
        if next_url is None:
            break
        full_url = base_url + next_url
        infos, next_url = extract_from_url(session, base_url + next_url) 
        for info in infos:
            download_gazette(session, info, full_url)
        all_infos += infos
    file.write_text(json.dumps(all_infos))


if __name__ == '__main__':
    Path('data').mkdir(exist_ok=True)
    session = requests.session()

    process_section(session, normal_gazette_url, 'normal.json')
    process_section(session, extraordinary_gazette_url, 'extraordinary.json')



