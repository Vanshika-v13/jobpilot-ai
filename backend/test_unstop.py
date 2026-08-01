import httpx
import json

url = 'https://unstop.com/api/public/opportunity/search-new?opportunity=jobs&oppstatus=open&per_page=5&page=1&searchTerm=python+developer'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}
r = httpx.get(url, headers=headers)
print('STATUS:', r.status_code)
data = r.json().get('data', {}).get('data', [])
for i, item in enumerate(data):
    print(f'{i+1}: {item.get("title")} | {item.get("organisation", {}).get("name")}')
