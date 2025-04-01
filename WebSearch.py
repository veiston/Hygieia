import hrequests
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

if __name__ == "__main__":
    search()
