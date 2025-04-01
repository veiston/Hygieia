import hrequests
import urllib.parse
from bs4 import BeautifulSoup

def search(url="https://www.terveyskirjasto.fi/"):
    '''Etsi URL-osoitteesta tietoa ja palauta käsitelty HTML-sisältö.'''
    try:
        response = hrequests.get(url)
        # Check for HTTP errors manually
        if response.status_code != 200:
            raise Exception(f"HTTP error: {response.status_code}")
        # Optionally, parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        print(soup.prettify())
        return response
    except Exception as e:
        print(f"Error occurred while fetching {url}: {e}")
        return None

def scrape_medical_info(query: str) -> str:
    """
    Build a search URL for Terveyskirjasto using the query,
    fetch the content, and extract text from paragraph tags.
    """
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.terveyskirjasto.fi/?q={encoded_query}"
    try:
        response = hrequests.get(search_url)
        if response.status_code != 200:
            raise Exception(f"HTTP error: {response.status_code}")
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        return content
    except Exception as e:
        print(f"Error occurred while scraping {search_url}: {e}")
        return ""

if __name__ == "__main__":
    search()
