import cloudscraper, re

s = cloudscraper.create_scraper()
r = s.get('https://www.seedhub.cc/s/%E5%A5%BD%E4%B8%9C%E8%A5%BF/', timeout=15)
html = r.text
cards = re.findall(r'title="([^"]+)"[^>]*class="image"[^>]*href="(/movies/\d+)/?"', html)
print(f'Movie cards: {len(cards)}')
for t, h in cards[:5]:
    print(f'  [{t}] {h}')
detail_hrefs = re.findall(r'href="([^"]+)"', html)
detail_movies = [h for h in detail_hrefs if re.search(r'/movies/\d+/?$', h)]
print(f'Detail hrefs matching /movies/digit: {detail_movies[:5]}')
print(f'Contains "好东西": {"好东西" in html}')
print(f'Contains "seedhub": {"seedhub" in html.lower()}')
