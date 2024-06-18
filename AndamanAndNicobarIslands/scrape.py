import json
from pathlib import Path
from pprint import pprint
from datetime import date, datetime, timedelta

import requests

main_url = 'http://andssw1.and.nic.in/doip/index.php/home/srchgazette'
dept_url = 'http://andssw1.and.nic.in/doip/index.php/fetch/alldept'
post_url = 'http://andssw1.and.nic.in/doip/index.php/fetch/srchGazette'


def clean_info(info):
    for k,v in info.items():
        info[k] = v.replace('&amp;','&')

def update_info(info):
    clean_info(info)
    i = info['id']
    issdocavailable = info['issdocavailable']
    refnum = info['refnum']
    fileno = info['fileno']
    if issdocavailable == "2":
        return
    if refnum in ['Tester', 'Hackerone', 'testing']:
        return
    if fileno in ['Tester', 'Hackerone', 'testing', 'dafdsff4554353']:
        return
    info['url'] = f'http://andssw1.and.nic.in/doip/uploads/gazette/s/{i}.pdf'

# copied from https://gist.github.com/srafay/19e0a13fe7e402f0a79715b1ed3f6560
def generate_form_data_payload(kwargs, boundary):
    FORM_DATA_STARTING_PAYLOAD = f'--{boundary}\r\nContent-Disposition: form-data; name="'
    FORM_DATA_MIDDLE_PAYLOAD = '"\r\n\r\n'
    FORM_DATA_ENDING_PAYLOAD = f'--{boundary}--'
    payload = ''
    for key, value in kwargs.items():
        payload += '{0}{1}{2}{3}\r\n'.format(FORM_DATA_STARTING_PAYLOAD, key, FORM_DATA_MIDDLE_PAYLOAD, value)
    payload += FORM_DATA_ENDING_PAYLOAD
    return payload

def get_dept_list(session):
    p = Path('data/dept_list.json')
    if p.exists():
        data = json.loads(p.read_text())
        return data

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': main_url
    }
    resp = session.get(dept_url, headers=headers, params={'ajax': 'true'})
    if not resp.ok:
        raise Exception(f'unable to retrieve page {dept_url}')
    data = resp.json()
    p.write_text(json.dumps(data))
    return data

def get_gazette_list(session, start_date, end_date):
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    print(f'getting gazette list for {start_date_str} to {end_date_str}')
    cookies = session.cookies.get_dict()
    csrf_test_name = cookies['csrf_cookie_name']
    post_data = {
        'dddept': '0',
        'ddcat': '0',
        'txtfileno': '',
        'txtregistryno': '',
        'txtrefno': '',
        'txtkeyword': '',
        'txtsubject': '',
        'txtfromdate': start_date_str,
        'txttodate': end_date_str,
        'csrf_test_name': csrf_test_name,
    }
    boundary = "----WebKitFormBoundaryecDC0QcQWcBRoF9a"
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Origin': 'http://andssw1.and.nic.in',
        'Pragma': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'referer': main_url,
        'X-Requested-With': 'XMLHttpRequest',
        'content-type': f"multipart/form-data; boundary={boundary}",
    }
    payload = generate_form_data_payload(post_data, boundary)
    resp = session.post(post_url, data=payload, headers=headers)
    if not resp.ok:
        raise Exception(f'unable to make form post to {main_url}')
    text = resp.text
    data = json.loads(text)
    for info in data:
        update_info(info)
    return data
    
def get_all(session):
    infos = []
    p = Path('data/all_infos.jsonl')
    done_till_date = date(1947, 1, 1)
    if p.exists():
        with open(p, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '':
                    continue
                entry = json.loads(line)
                infos.append(entry)
                issue_date_str = entry['issuedate']
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
                if issue_date > done_till_date:
                    done_till_date = issue_date

    curr_date = date.today()
    start_date = done_till_date + timedelta(days=1)
    if start_date > curr_date:
        return infos
    while True:
        end_date = start_date + timedelta(days=365)
        if end_date > curr_date:
            end_date = curr_date
        new_infos = get_gazette_list(session, start_date, end_date)
        with open(p, 'a') as f:
            for info in new_infos:
                f.write(json.dumps(info))
                f.write('\n')
        infos += new_infos
        if curr_date == end_date:
            break
        start_date = end_date + timedelta(days=1)
    return infos

def download_pdfs(session, all_gazette_infos):
    gazette_dir = Path('data/gazettes/')
    gazette_dir.mkdir(exist_ok=True, parents=True)
    for info in all_gazette_infos:
        i = info['id']
        p = gazette_dir / f'{i}.pdf'
        if p.exists():
            continue
        url = info.get('url', None)
        if url is None:
            continue
        print(f'downloading file from {url}')
        resp = session.get(url)
        if not resp.ok:
            raise Exception(f'unable to retrieve gazette at {url}')
        data = resp.content
        p.write_bytes(data)

if __name__ == '__main__':
    session = requests.session()
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve page {main_url}')
    Path('data').mkdir(exist_ok=True)
    dept_list = get_dept_list(session)
    #pprint(dept_list)
    all_gazette_infos = get_all(session)
    #pprint(all_gazette_infos)
    download_pdfs(session, all_gazette_infos)
