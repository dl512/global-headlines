import requests
import json
import datetime
import os
from bs4 import BeautifulSoup


def get_raw_html(url: str) -> dict:

    date = datetime.datetime.today().strftime("%Y-%m-%d")

    try:
        html_text = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).text
        soup = BeautifulSoup(html_text, 'lxml')

        return {"date": date,
                "html": soup.prettify()}

    except requests.Timeout:
        print(f'Request timed out after 30 seconds: {url}')
    except ConnectionError:
        print(f'Invalid link: {url}')
    except Exception as e:
        print(f'Error fetching {url}: {str(e)}')