import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import traceback
import urllib.parse
import urllib.request


class AbstractCommonWeb:
    __url = ''

    def __init__(self):
        pass

    @classmethod
    def get_all_links(cls, site: str):
        # Send a GET request to the URL
        response = requests.get(site)

        # Check if the request was successful
        if response.status_code == 200:
            # Create a BeautifulSoup object and specify the parser
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all <a> tags in the HTML content
            a_tags = soup.find_all('a')

            # Extract the href attribute (link) from each <a> tag
            links = [a.get('href') for a in a_tags]
            if len(links) < 10: # если меньше 10 ссылок на сайте, то что-то не так
                return cls._extremely_hard_getter(site)
            # Filter out any None values and return the list of links
            #return list(filter(None, links)) - сейчас "any None values" отфильтровываются отдельно для каждого сайта
            return links
        elif response.status_code == 401:
            return cls._extremely_hard_getter(site)
        raise f"Failed to retrieve the webpage. Status code: {response.status_code}"

    #if site have a defense from parsing: (это долго и в некоторых случаях не очень этично)
    # и ещё тут нужен хром - на сервере, где будет запущен бот.
    # позже что-нибудь надо сообразить с более элегантными решениями (пуппет, "безголовые" браузеры)
    @classmethod
    def _extremely_hard_getter(cls, site: str):
        driver = webdriver.Chrome()
        driver.get(site)

        # Wait for JavaScript to load (you can also use explicit waits)
        driver.implicitly_wait(10)  # Waits up to 10 seconds until elements are available

        # Now that the page is fully loaded, get the page source
        html = driver.page_source
        driver.quit()

        # Use BeautifulSoup to parse the page source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract all links
        links = soup.find_all('a', href=True)
        return [a.get('href') for a in links]

    @classmethod
    def sites_filter(cls, criteria=0):
        stack = traceback.extract_stack()
        raise Exception(f"Instances of the {cls.__name__} class cannot call the method "
                        f"{str(stack[-1]).split()[-1].split('>')[0]}")

    @staticmethod
    def verify_url(url):
        # Checking url correctness
        result = urllib.parse.urlparse(url)
        is_valid = all([result.scheme, result.netloc])
        if not is_valid:
            return False, "URL isn\'t correct"
        # Checking url availability
        try:
            with urllib.request.urlopen(url) as response:
                if response.status_code == 200:
                    return True, "URL is correct and accessible"
                else:
                    return False, "Web page unavailable"
        except Exception as e:
            return False, f"Error when accessing URL: {e}"


if __name__ == '__main__':
    AbstractCommonWeb.sites_filter()

