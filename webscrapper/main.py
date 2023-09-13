from dataclasses import dataclass
from json import dump
from logging import basicConfig, DEBUG, error
from typing import Any, Generator

from bs4 import BeautifulSoup, ResultSet, Tag
from fake_useragent import UserAgent
from requests import Response, Session


class SoupKitchen:
    @staticmethod
    def make_soup(markup: str) -> BeautifulSoup:
        soup: BeautifulSoup = BeautifulSoup(markup=markup, features='html.parser')

        return soup


class Website:
    user_agent = UserAgent()

    def __init__(self, url: str, *, cookies: dict = None, params: dict = None) -> None:
        self.url: str = url
        self.cookies: dict = cookies or {}
        self.params: dict = params or {}

        self.__markup = self.__spider = self.__domain = None

    @property
    def markup(self) -> str:
        if not self.__markup:
            with Session() as session:
                session.headers['User-Agent']: str = self.user_agent.random

                response: Response = session.get(url=self.url, params=self.params, cookies=self.cookies)
                markup: str = response.text

            self.__markup = markup

        return self.__markup

    @property
    def spider(self) -> BeautifulSoup:
        if not self.__spider:
            self.__spider: BeautifulSoup = SoupKitchen.make_soup(markup=self.markup)

        return self.__spider


@dataclass
class Item:
    link: str
    price: int


class HrefExtractor:
    limiter = '"'

    @staticmethod
    def extract(tag: Tag, attribute: str) -> str:
        string = tag.get(attribute)

        start_index = string.index('"') + 1
        end_index = string.index('"', start_index)

        return string[start_index:end_index]


class Product:
    url = 'https://n-katalog.ru'

    def __init__(self, *, link: str, price: int):
        self.link = link
        self.price = price

        ######
        self.__the_cheapest_offer = None

    @property
    def the_cheapest_offer(self):
        if not self.__the_cheapest_offer:
            spider: BeautifulSoup = Website(url=self.link).spider

            offers: ResultSet = spider.find_all(class_='shop-108767 priceElem price-elem-js')
            items = []

            for offer in offers:
                information: Tag = offer.find(class_='where-buy-price')

                href: str = HrefExtractor.extract(tag=information.find(class_='yel-but-2'), attribute='onmouseover')
                link: str = self.url + href
                price: int = int(information.find_next().text.split()[0])

                items.append(Item(link=link, price=price))

            self.__the_cheapest_offer = min(items, key=lambda item: item.price)

        return self.__the_cheapest_offer


class Page:
    url = 'https://n-katalog.ru'

    def __init__(self, *, keyword: str):
        self.spider = Website(url=self.url + '/search', params={'keyword': keyword}).spider

        ######
        self.__the_cheapest_model = None

    @property
    def products(self) -> Generator[Product, Any, None]:
        models: ResultSet = self.spider.find_all(class_='model-short-block')

        for model in models:
            link: str = self.url + model.find(class_='list-img h').find_next().get('href')
            price: Tag = model.find(id='model-price-range')

            if price:
                product: Product = Product(link=link, price=int(price.text.split()[1]))
            else:  # if there are no offers, then skip
                continue

            yield product

    @property
    def the_cheapest_model(self):
        if not self.__the_cheapest_model:
            if any(self.products):
                self.__the_cheapest_model = min(self.products, key=lambda product: product.price)
            else:
                return None

        return self.__the_cheapest_model


class DataSheet:
    path = 'webscrapper/data/raw.json'

    def __init__(self, **kwargs) -> None:
        self.details = kwargs

    def to_json(self):
        with open(file=self.path, mode='w', encoding='UTF-8') as file:
            dump(obj=self.details, fp=file, indent=2, ensure_ascii=False)


class Scrapper:
    @staticmethod
    def main() -> None:
        basicConfig(level=DEBUG)  # enabling logging

        keyword = 'Palit GeForce RTX 3060'
        page = Page(keyword=keyword)
        the_cheapest_model = page.the_cheapest_model

        if the_cheapest_model is None:
            error(msg='Нет доступных предложений')
            quit()

        the_cheapest_offer = the_cheapest_model.the_cheapest_offer

        sheet = DataSheet(keyword=keyword, price=the_cheapest_offer.price, link=the_cheapest_offer.link)
        sheet.to_json()


if __name__ == '__main__':
    Scrapper.main()
