from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from captcha.auto import save_captcha

main_url = 'https://egazette.chd.gov.in/'

def get_img(session):
    resp = session.get(main_url)
    if not resp.ok:
        raise Exception(f'unable to retrieve {main_url}')
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    home_div = soup.find('div', {'id': 'home'})
    img = home_div.find('img')
    img_url = main_url + img.attrs['src']
    resp = session.get(img_url)
    if not resp.ok:
        raise Exception(f'unable to get img at {img_url}')

    save_captcha(BytesIO(resp.content))



if __name__ == '__main__':
    session = requests.session()
    for i in range(50):
        print(f'collecting img no: {i}')
        get_img(session)

