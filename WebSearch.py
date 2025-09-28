import requests as hrequests #hrequests is being a bitch but leaving it here for the future
import urllib.parse
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from urllib.parse import urlparse, parse_qs, unquote

HEADERS = {"User-Agent": "Hygieia/1.0 (+https://example.org)"}

# Patterns for URLs we usually want to skip (generic landing pages)
IGNORE_HOST_PATHS = {
    "terveyskirjasto.fi": [
        "laakarikirja-duodecim",
        "god-medicinsk-praxis-for-patienter",
        "kayvan-hoidon-potilasversiot",
        "etusivu",
        "index",
    ],
}


def should_ignore_url(url: str) -> bool:
    # return True for URLs matching our ignore list
    try:
        parsed = urlparse(url)
        host = parsed.netloc or ""
        path = parsed.path or ""
        for host_sub, patterns in IGNORE_HOST_PATHS.items():
            if host_sub in host:
                for pat in patterns:
                    if pat in path or pat in url:
                        return True
    except Exception:
        return False
    return False

def find_first_site_result(domain: str, query: str, timeout: int = 10) -> str:
    # get candidates from DuckDuckGo + site fallback, pick best match
    candidates = []
    encoded_query = urllib.parse.quote(f"site:{domain} {query}")
    search_url = f"https://duckduckgo.com/html/?q={encoded_query}"
    try:
        resp = hrequests.get(search_url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    # DDG results: links or redirect wrappers (/l/?uddg=...)
        for a in soup.find_all('a', href=True):
            if not isinstance(a, Tag):
                continue
            href_val = a.get('href')
            if href_val is None:
                continue
            href = str(href_val)
            # extract uddg redirect
            if '/l/?' in href or href.startswith('/l/?'):
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                uddg = qs.get('uddg')
                if uddg:
                    url = unquote(str(uddg[0]))
                    if url.startswith('//'):
                        url = 'https:' + url
                    if domain in urlparse(str(url)).netloc and not should_ignore_url(url):
                        if url not in candidates:
                            candidates.append(url)
                continue
            # normalize
            if href.startswith('//'):
                abs_href = 'https:' + href
                if domain in urlparse(str(abs_href)).netloc and not should_ignore_url(abs_href):
                    if abs_href not in candidates:
                        candidates.append(abs_href)
                continue
            if href.startswith('http'):
                if domain in urlparse(str(href)).netloc and not should_ignore_url(href):
                    if href not in candidates:
                        candidates.append(href)
    except Exception:
        pass

    # try site-specific search too
    try:
        fb = _site_search_fallback(domain, query, timeout=timeout)
        if fb and not should_ignore_url(fb) and fb not in candidates:
            candidates.append(fb)
    except Exception:
        pass

    # score candidates; accept only if title has 1 token or snippet has >=2 tokens
    if candidates:
        best = None
        best_score = 0
        for c in candidates:
            try:
                score, title_hits, snippet_hits = _score_candidate(c, query, timeout=timeout)
                if title_hits >= 1 or snippet_hits >= 2:
                    return c
                if score > best_score:
                    best_score = score
                    best = c
            except Exception:
                continue
        if best and best_score > 0:
            return best
        # fallback: return first candidate if nothing scores well
        return candidates[0]

    return ""


def _score_candidate(url: str, query: str, timeout: int = 6):
    # fetch a page and count token hits in title/snippet; return (score, title_hits, snippet_hits)
    qtokens = [t for t in query.lower().split() if t]
    try:
        resp = hrequests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = ""
        ttag = soup.find('title')
        if isinstance(ttag, Tag):
            title = ttag.get_text(strip=True).lower()
    # snippet from first few paragraphs
        paragraphs = []
        article = soup.find('article')
        if isinstance(article, Tag):
            paragraphs = article.find_all('p')
        else:
            paragraphs = soup.find_all('p')
        snippet = " ".join([p.get_text(separator=' ', strip=True) for p in paragraphs[:5]])[:1000].lower()
        title_hits = 0
        snippet_hits_set = set()
        score = 0
        for t in qtokens:
            if t in title:
                title_hits += 1
                score += 3
            if t in snippet:
                snippet_hits_set.add(t)
                score += 1
        snippet_hits = len(snippet_hits_set)
        return score, title_hits, snippet_hits
    except Exception:
        return 0, 0, 0


def _site_search_fallback(domain: str, query: str, timeout: int = 10) -> str:
    try:
        encoded = urllib.parse.quote(query)
        site_root = f"https://{domain}"
        # try common search path used by the site
        search_url = f"{site_root}/haku?q={encoded}"
        resp = hrequests.get(search_url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Prefer links that look like article paths, e.g. /trvXXXXX or /sisalto/... containing useful content
        for a in soup.find_all('a', href=True):
            if not isinstance(a, Tag):
                continue
            href_val = a.get('href')
            if href_val is None:
                continue
            href = str(href_val)
            # normalized absolute url
            if href.startswith('/'):
                candidate = site_root + href
            elif href.startswith('//'):
                candidate = 'https:' + href
            else:
                candidate = href
            # heuristics: prefer '/trv' article pages or '/sisalto' content pages
            path = urlparse(str(candidate)).path
            if path.startswith('/trv') or '/sisalto/' in path or '/sisalto' in path:
                if should_ignore_url(candidate):
                    continue
                return str(candidate)
        # fallback: first absolute link for the domain
        for a in soup.find_all('a', href=True):
            if not isinstance(a, Tag):
                continue
            href_val = a.get('href')
            if href_val is None:
                continue
            href = str(href_val)
            if href.startswith('/'):
                candidate = site_root + href
            elif href.startswith('//'):
                candidate = 'https:' + href
            else:
                candidate = href
            if domain in urlparse(str(candidate)).netloc:
                if should_ignore_url(candidate):
                    continue
                return str(candidate)
    except Exception:
        return ""
    return ""


def scrape_medical_info(query: str, domain: str = "terveyskirjasto.fi") -> str:
    '''Search the given domain and return top result'''
    try:
        first_url = find_first_site_result(domain, query)
        if not first_url:
            return ""
        resp = hrequests.get(first_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # prefer article tag
        article = soup.find('article')
        if isinstance(article, Tag):
            paragraphs = article.find_all('p')
        else:
            paragraphs = soup.find_all('p')
        texts = []
        for p in paragraphs:
            if not isinstance(p, Tag):
                continue
            txt = p.get_text(strip=True)
            if txt:
                texts.append(str(txt))
        content = "\n\n".join(texts[:10])
        if content:
            return f"Source: {first_url}\n\n{content}"
        return ""
    except Exception:
        return ""


if __name__ == "__main__":
    print(scrape_medical_info("iho"))
