import json
from pathlib import Path
from pprint import pprint
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

main_url = 'https://dpns.assam.gov.in'

def get_counts(pane_div):
    count_span = pane_div.find('span', {'class': 'total-row'})
    total_count = int(count_span.text.strip())
    pager_ul = pane_div.find('ul', { 'class': 'pager' })
    last_page_idx = 0
    if pager_ul is not None:
        last_page_li = pager_ul.find('li', {'class': 'pager-last'})
        last_page_url = last_page_li.find('a').attrs['href']
        last_page_idx = int(last_page_url.split('=')[-1])
    return total_count, last_page_idx

def collect_items(pane_div, page_item_file):
    items = []
    item_list_div = pane_div.find('div', {'class': 'item-list'})
    lis = item_list_div.find_all('li')
    for li in lis:
        a = li.find('a')
        items.append([a.text.strip(), a.attrs['href']])
    page_item_file.write_text(json.dumps(items))
    return items


def collect_section(session, category, link):
    cat_dir = Path(f'data/{category}/')
    cat_dir.mkdir(exist_ok=True, parents=True)
    section_name = link.split('/')[-1]
    section_dir = cat_dir / section_name
    section_dir.mkdir(exist_ok=True, parents=True)

    print(f'handling page 0')
    full_url = main_url + link
    resp = session.get(full_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve page {full_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    pane_div = soup.find('div', {'class': 'pane-content'})
    total_count, last_page_idx = get_counts(pane_div)
    page_item_file = section_dir / '0.json'
    if page_item_file.exists():
        items = json.loads(page_item_file.read_text())
    else:
        items = collect_items(pane_div, page_item_file)
    for i in range(1, last_page_idx + 1):
        print(f'handling page {i}/{last_page_idx}')
        page_item_file = section_dir / f'{i}.json'
        if page_item_file.exists():
            items += json.loads(page_item_file.read_text())
            continue
        resp = session.get(full_url, params={'page': str(i)})
        if not resp.ok:
            raise Exception(f'unable to retrieve page {full_url}, page: {i}')
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        pane_div = soup.find('div', {'class': 'pane-content'})
        items += collect_items(pane_div, page_item_file)
    return items


def get_top_links(session):
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve page {main_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    lis = soup.find_all('li', {'data-level': '2'})
    extraordinary_links = []
    weekly_links = []
    for li in lis:
        li_text = li.text.strip()
        if li_text.startswith('Extraordinary'):
            link = li.find('a').attrs['href']
            extraordinary_links.append(link)
        if li_text.startswith('Weekly Gazette'):
            link = li.find('a').attrs['href']
            weekly_links.append(link)
    return extraordinary_links, weekly_links

def download_gazette(session, info):
    category = info['category']
    cat_dir = Path(f'data/gazettes/{category}/')
    cat_dir.mkdir(exist_ok=True, parents=True)
    for url in info['urls']:
        fname = url.split('/')[-1]
        gaz_file = cat_dir / fname
        if gaz_file.exists():
            return
        print(f'downloading file from {url}')
        resp = session.get(url)
        if not resp.ok:
            raise Exception(f'unable to download {url}')
        gaz_file.write_bytes(resp.content)


def extract_urls(html):
    soup = BeautifulSoup(html, 'html.parser')
    pane_div = soup.find('div', {'class': 'pane-content'})
    if pane_div is None:
        return []
    table = pane_div.find('table')
    if table is None:
        return []
    a_s = table.find_all('a', {'class': 'file-pdf'})
    urls = [ a.attrs['href'] for a in a_s ]
    return urls


def populate_gazette_links(session, items):
    links_file = Path('data/links.jsonl')
    known_items = set()
    infos = []
    if links_file.exists():
        with open(links_file, 'r') as f:
            for line in f:
                line = line.strip()
                info = json.loads(line)
                infos.append(info)
                key = (info['name'], info['link'], info['category'])
                known_items.add(key)
    with open(links_file, 'a') as f:
        for item in items:
            key = tuple(item)
            if key in known_items:
                continue
            name = item[0]
            link = item[1]
            category = item[2]
            full_url = main_url + link
            print(f'processing {full_url}')
            resp = session.get(full_url)
            if not resp.ok:
                raise Exception(f'unable to retrieve page {full_url}')
            html = resp.text
            urls = extract_urls(html)
            info = {'name': name,
                    'link': link,
                    'category': category,
                    'urls': urls}
            infos.append(info)
            f.write(json.dumps(info))
            f.write('\n')
    return infos


if __name__ == '__main__':
    Path('data').mkdir(exist_ok=True)
    session = requests.session()
    extraordinary_links, weekly_links = get_top_links(session)
    items = []
    for link in extraordinary_links:
        print(f'handling section {link}')
        new_items = collect_section(session, 'extraordinary', link)
        new_items = [ i + ['extraordinary'] for i in new_items ]
        items += new_items
 
    for link in weekly_links:
        print(f'handling section {link}')
        new_items = collect_section(session, 'weekly', link)
        new_items = [ i + ['weekly'] for i in new_items ]
        items += new_items

    infos = populate_gazette_links(session, items)

    for info in infos:
        download_gazette(session, info)
