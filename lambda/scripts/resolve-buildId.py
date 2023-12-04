#!/opt/homebrew/bin/python3
import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.streetfighter.com/6/buckler/ja-jp'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}

resp = requests.get(url, headers=headers)
html_content = resp.text

# BeautifulSoupを使ってHTMLを解析
soup = BeautifulSoup(html_content, 'html.parser')

# "__NEXT_DATA__"のスクリプトタグを見つける
script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

# スクリプトタグの中身（JSONデータ）を取得し、JSONとして解析
json_data = json.loads(script_tag.string)

# JSONデータからbuildIdの値を取り出す
build_id = json_data.get('buildId', None)
print("Build ID:", build_id)