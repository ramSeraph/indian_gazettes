import json
from io import BytesIO
from pathlib import Path
from pprint import pprint
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

from captcha.auto import guess

# !!!!! NOTE: THIS DOES NOT WORK  !!!!!!!
# the webiste is weird, hard to make it work rationally from the browser, but it is possible, I have not manged to replciate it here though.

main_url = 'https://egazette.chd.gov.in/'

def extract_entries(soup):
    entries = []
    table = soup.find('table', {'id': 'ContentPlaceHolder1_GridView1'})
    trs = table.find_all('tr', recursive=False)
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        if len(tds) == 0:
            continue
        department = tds[1].text.strip()
        notification_no = tds[2].text.strip()
        notification_date = tds[3].text.strip()
        subject = tds[4].text.strip()
        category = tds[5].text.strip()
        gazette_no = tds[6].text.strip()
        dbutton = tds[7].find('input')
        dbutton_name = dbutton.attrs['name']
        entry = {
            'department': department,
            'notification_no': notification_no,
            'notification_date': notification_date,
            'subject': subject,
            'category': category,
            'gazette_no': gazette_no,
            'dbutton_name': dbutton_name,
        }
        entries.append(entry)
    return entries


def download_entry(session, entry, hidden_fields):
    gazette_no = entry['gazette_no']
    gazette_fname = gazette_no.replace('/', '_') + '.pdf'
    gaz_dir = Path('data/gazettes/')
    gaz_dir.mkdir(exist_ok=True, parents=True)
    gaz_file = gaz_dir / gazette_fname
    if gaz_file.exists():
        return
    post_data = {}
    post_data.update(hidden_fields)
    post_data.update({
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__LASTFOCUS': '',
    })
    post_data[entry['dbutton_name']] = 'Download'
    print(f'downloading gazette: {gazette_no}')
    resp = session.post(main_url, data=post_data)
    if not resp.ok:
        print(resp.text)
        raise Exception(f'unable to download file: {gaz_fname}')
    gaz_file.write_bytes(resp.content)


def get_hidden_fields(soup):
    hidden_inputs = soup.find_all('input', { 'type': 'hidden' })
    base_form_data = {}
    for inp in hidden_inputs:
        ident = inp.attrs['id']
        val = inp.attrs.get('value', '')
        base_form_data[ident] = val
    return base_form_data

def get_current_year_gazettes(session):
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to get {main_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    entries = extract_entries(soup)
    hidden_fields = get_hidden_fields(soup)
    for entry in entries:
        download_entry(session, entry, hidden_fields)
        session = requests.session()
    for entry in entries:
        del entry['dbutton_name']

    # TODO: consider only append and check for duplicates?
    with open('data/entries.jsonl', 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry))
            f.write('\n')

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': 'egazette.chd.gov.in',
    'Origin': 'https://egazette.chd.gov.in',
    'Pragma': 'no-cache',
    'Referer': 'https://egazette.chd.gov.in/',
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

def get_older_gazettes(start_date, end_date, already_seen):
    print(f'getting gazettes for {start_date} to {end_date}')
    attempts = 0
    while True:
        attempts += 1
        if attempts > 20:
            raise Exception('unable to continue due to many captcha failures')
        session = requests.session()
        resp = session.get(main_url)
        if not resp.ok:
            raise Exception(f'unable to get {main_url}')
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        hidden_fields = get_hidden_fields(soup)
        home_div = soup.find('div', {'id': 'home'})
        img = home_div.find('img')
        img_url = main_url + img.attrs['src']
        resp = session.get(img_url)
        if not resp.ok:
            raise Exception(f'unable to get img at {img_url}')
        img_f = BytesIO(resp.content)
        captcha = guess(img_f)
        print(f'entered captcha: {captcha}')
        post_data = {}
        post_data.update(hidden_fields)
        post_data.update({
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
        })
        start_date_str = start_date.strftime('%m/%d/%Y')
        end_date_str = end_date.strftime('%m/%d/%Y')
        post_data.update({
            'ctl00$ContentPlaceHolder1$ddDepartment': '',
            'ctl00$ContentPlaceHolder1$txtfromDate': start_date_str,
            'ctl00$ContentPlaceHolder1$txtToDate': end_date_str,
            'ctl00$ContentPlaceHolder1$searchtext': captcha,
            'ctl00$ContentPlaceHolder1$btnSearch': 'Search',
            'ctl00$ContentPlaceHolder1$ddlCategoryType': '',
            'ctl00$ContentPlaceHolder1$txtfromDate2': '',
            'ctl00$ContentPlaceHolder1$txtToDate2': '',
            'ctl00$ContentPlaceHolder1$TextBox6': '',
            'ctl00$ContentPlaceHolder1$txtNotificationNo': '',
            'ctl00$ContentPlaceHolder1$txtfromDate3': '',
            'ctl00$ContentPlaceHolder1$txtToDate3': '',
            'ctl00$ContentPlaceHolder1$TextBox9': '',
            'ctl00$ContentPlaceHolder1$DDListDepartment1': '',
            'ctl00$ContentPlaceHolder1$DDlistGazette': '',
            'ctl00$ContentPlaceHolder1$txtfromDate4': '',
            'ctl00$ContentPlaceHolder1$txtToDate4': '',
            'ctl00$ContentPlaceHolder1$txtsearch4': '',
            'ContentPlaceHolder1_GVNotification_length': '10',
            'ctl00$ContentPlaceHolder1$txtMobileNo': '',
        })
        for k,v in post_data.items():
            if k.startswith('_'):
                continue
            print(f'{k}: {v}')
        #print(post_data)
        resp = session.post(main_url, data=post_data, headers=headers)
        if not resp.ok:
            raise Exception(f'unable to post to get data for {start_date} {end_date}')
        html = resp.text
        if html.find("alert('Please Enter Captcha')") != -1:
            print('captcha failed.. trying again')
            continue
        break
    soup = BeautifulSoup(html, 'html.parser')
    entries = extract_entries(soup)
    print(f'found {entries}') 
    with open('data/entries.jsonl', 'a') as f:
        for entry in entries:
            key = (entry['gazette_no'], entry['notification_no'])
            if key in already_seen:
                continue
            already_seen.add(key)
            download_entry(session, entry, hidden_fields)
            del entry['dbutton_name']
            f.write(json.dumps(entry))
            f.write('\n')
            session = requests.session()


if __name__ == '__main__':
    session = requests.session()
    #get_current_year_gazettes(session)

    known_earliest_date = date(2019, 1, 1)
    latest_seen = known_earliest_date
    list_file = Path('data/entries.jsonl')
    already_seen = set()
    if list_file.exists():
        with open(list_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '':
                    continue
                entry = json.loads(line)
                gazette_no = entry['gazette_no']
                notification_no = entry['notification_no']
                already_seen.add((gazette_no, notification_no))
                gazette_date_str = gazette_no.split('-')[-1]
                gazette_date = datetime.strptime(gazette_date_str, '%d/%m/%Y').date()
                if gazette_date > latest_seen:
                    latest_seen = gazette_date
    curr_date = date.today() - timedelta(days=1)
    start_date = latest_seen
    end_date = start_date + timedelta(days=365)
    while True:
        if end_date > curr_date:
            end_date = curr_date
        get_older_gazettes(start_date, end_date, already_seen)
        if end_date == curr_date:
            break
        start_date = end_date + timedelta(days=1)
        end_date = start_date + timedelta(days=365)

