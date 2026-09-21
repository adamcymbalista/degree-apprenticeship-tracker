"""One-off diagnostic: fetch the live findapprenticeship search page exactly
the way app/sources/findapprenticeship.py does, and dump what we actually got
back so we can see why 0 listings are being parsed. Safe to delete after use.
"""
import re
import requests

from app.http_client import get
from app.sources.findapprenticeship import BASE_URL, SEARCH_PATH, REFERENCE_RE

params = {
    "searchTerm": "software",
    "location": "London",
    "distance": "all",
    "sort": "AgeDesc",
    "pageNumber": 1,
}

print("=== via app.http_client.get() (what the real scraper uses) ===")
resp = get(BASE_URL + SEARCH_PATH, params=params, timeout=20, delay_seconds=0)
if resp is None:
    print("get() returned None - request failed or blocked, see WARNING logs above.")
else:
    print("status:", resp.status_code)
    print("final url:", resp.url)
    print("content length:", len(resp.text))
    print("contains 'results found':", "results found" in resp.text)
    print("contains '/apprenticeship/reference/':", "/apprenticeship/reference/" in resp.text)
    print("count of reference matches:", len(REFERENCE_RE.findall(resp.text)))
    with open("diagnose_output.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("saved full HTML to diagnose_output.html")

print()
print("=== via plain requests (no robots check, no rate limit) ===")
r2 = requests.get(BASE_URL + SEARCH_PATH, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
print("status:", r2.status_code)
print("final url:", r2.url)
print("content length:", len(r2.text))
print("contains 'results found':", "results found" in r2.text)
print("contains '/apprenticeship/reference/':", "/apprenticeship/reference/" in r2.text)
