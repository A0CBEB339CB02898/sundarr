"""显式手动搜索 API 检查，不参与默认 pytest。"""

import json
import urllib.parse
import urllib.request


def main() -> None:
    url = "http://127.0.0.1:8080/search?" + urllib.parse.urlencode({"q": "好东西", "limit": 20})
    with urllib.request.urlopen(url, timeout=15) as response:
        data = json.loads(response.read())
    print(f"count={data['count']}")
    print(f"source_results={[(item['source_id'], item['count']) for item in data['source_results']]}")
    if not data["results"]:
        print("NO RESULTS")
        return
    result = data["results"][0]
    print(f"title={result['title']}")
    print(f"has_more_links={result.get('has_more_links')}")
    print(f"source_url={result.get('source_url')}")
    print(f"links_count={len(result.get('links', []))}")


if __name__ == "__main__":
    main()
