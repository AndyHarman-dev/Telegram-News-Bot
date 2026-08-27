from app.pipelines.pipes.parser.parser_web.web_abstract import AbstractCommonWeb


class NationalGeographic(AbstractCommonWeb):
    __url: str = 'https://www.nationalgeographic.com'
    topics = ['animals', 'environment', 'history', 'science', 'travel']
    gen_ = ['premium']

    def __init__(self):
        super().__init__()  # May be will be useful

    @classmethod
    def sites_filter(cls, criteria=0) -> list:
        links = []
        for topic in cls.topics:
            for link in cls.get_all_links(f'{cls.__url}/{topic}'):
                if cls.verify_url(link)[0]:
                    if link.find(f'/{topic}/article/') != -1:
                        links.append(link)
                    else:
                        for item in cls.gen_:
                            if link.find(f'/{item}/article/') != -1:
                                links.append(link)
                                break
        return links


if __name__ == '__main__':
    print(*NationalGeographic.sites_filter(), sep='\n')
