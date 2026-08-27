import re
from app.pipelines.pipes.parser.parser_web.web_abstract import AbstractCommonWeb


class Dailykos(AbstractCommonWeb):
    __url: str = 'https://www.dailykos.com'

    def __init__(self):
        super().__init__()  # May be will be useful

    @classmethod
    def sites_filter(cls, criteria=0) -> list:
        links = []
        pattern = r"stories/(\d{4})/(\d{1,2})/(\d{1,2})"
        for link in cls.get_all_links(cls.__url):
            if cls.verify_url(link)[0] and re.search(pattern, link):
                links.append(link)
            else:
                link = cls.__url + link
                if cls.verify_url(link)[0] and re.search(pattern, link):
                    links.append(link)
        return links


if __name__ == '__main__':
    print(*Dailykos.sites_filter(), sep='\n')
