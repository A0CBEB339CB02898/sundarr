import json, urllib.request, urllib.parse

url = 'http://127.0.0.1:8080/search?' + urllib.parse.urlencode({'q': '好东西', 'limit': 20})
r = urllib.request.urlopen(url)
data = json.loads(r.read())
print(f'count={data["count"]}')
print(f'source_results={[(s["source_id"], s["count"]) for s in data["source_results"]]}')
if data['results']:
    res = data['results'][0]
    print(f'title={res["title"]}')
    print(f'has_more_links={res.get("has_more_links")}')
    print(f'source_url={res.get("source_url")}')
    print(f'links_count={len(res.get("links", []))}')
else:
    print('NO RESULTS')
