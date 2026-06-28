
import sys
import requests
from bs4 import BeautifulSoup
from collections import Counter

def analyze(url: str):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    words = [w.lower() for w in text.split() if len(w) > 3]
    counter = Counter(words)

    print(f"URL: {url}")
    print(f"Total words (len>3): {len(words)}")
    print("Top 20 words:")
    for w, c in counter.most_common(20):
        print(f"{w}: {c}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 web_analyzer.py <URL>")
        sys.exit(1)
    analyze(sys.argv[1])
