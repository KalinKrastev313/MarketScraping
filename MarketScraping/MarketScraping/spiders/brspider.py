import scrapy
import re

from MarketScraping.items import Product

from collections import namedtuple

StorageData = namedtuple('StorageData', ['Name', 'Street', 'Number', 'Amount'])


class BrspiderSpider(scrapy.Spider):
    name = "brspider"
    allowed_domains = ["mr-bricolage.bg"]
    start_urls = ["https://mr-bricolage.bg/instrumenti/elektroprenosimi-instrumenti/vintoverti/c/006003013"]
    counter = 0

    def parse(self, response):
        yield from self.parse_search_results_page(response)
        last_page_number = int(response.css("body > app-root > brico-storefront > main > cx-page-layout.BricolageSpaListPageTemplate > cx-page-slot.BricoListContainerSlot.has-components > brico-listpage > brico-plp > div.plp-content > div > div:nth-child(4) > div > brico-pagination > nav > ul > li:nth-child(6) > a::text").get().strip())
        for page_number in range(1, last_page_number + 1):
            print(f"This is the page number {page_number}")
            next_page_url = self.start_urls[0] + '?currentPage=' + str(page_number)
            yield response.follow(next_page_url, callback=self.parse_search_results_page)

    def parse_search_results_page(self, response):
        products = response.css(".product__title")

        for product in products:
            relative_url = product.css("a::attr(href)").get()
            yield response.follow(relative_url, callback=self.parse_product_page)

    def parse_product_page(self, response):
        title = response.css("brico-pdp-title h1::text").get()
        image_dict = self.get_images_urls_dict(response)
        table_values = self.extract_table_data(response)
        price = self.get_price(response)
        rating = response.css(".rating-count::text").get()

        title = self.ensure_brand_in_the_title(title, table_values)
        product_code = re.search(r"\d+$", response.url).group()

        item = Product(
            title=title,
            url=response.url,
            price=price,
            rating=rating,
            images=image_dict,
            table_values=table_values
        )

        yield scrapy.Request(
            url=self.build_storage_url(product_code),
            callback=self.__parse_storage_data_json,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            meta={"item": item}
        )

    def get_images_urls_dict(self, response):
        image_urls = response.css(".swiper-slide img::attr(src)").getall()
        return {
            f"image{i + 1}": url
            for i, url in enumerate(image_urls)
        }

    def get_price(self, response):
        price_base = (response.css(".product__price-value::text").get()).replace('\n', '').strip()
        price_fraction = (response.css(".product__price .fraction::text").get()).replace('\n', '').strip()
        if price_fraction:
            return price_base + '.' + price_fraction
        return price_base

    def extract_table_data(self, response):
        labels = response.css(".product-classification-table tbody tr td:nth-child(1)::text").getall()
        values = response.css(".product-classification-table tbody tr td:nth-child(2) p::text").getall()
        values = [val.strip() for val in values]

        table_values = {spec: value for spec, value in zip(labels,
                                                           values)}
        return table_values

    def ensure_brand_in_the_title(self, title, table_values):
        if 'Марка' in table_values.keys():
            if not table_values['Марка'].upper() in title.upper():
                title = f"[{table_values['Марка']}] {title}"
        return title

    def build_storage_url(self, product_code):
        return f"https://api.mr-bricolage.bg/occ/v2/bricolage-spa/products/{product_code}/stock?fields=stores(name,displayName,address(streetname,streetnumber,town),stockInfo(FULL))&longitude=0&latitude=0"

    def __parse_storage_data_json(self, response):
        def __get_store_tuple_text_summary(store_tuple: StorageData):
            return f"Магазин {store_tuple.Name} на адрес {store_tuple.Street} №{store_tuple.Number} има наличност {store_tuple.Amount} продукта"
        item = response.meta["item"]
        # import pdb; pdb.set_trace()
        stores_summarized_data = []
        data = response.json()
        for store in data['stores']:
            store_data = StorageData(Name=store['displayName'],
                                     Street=store['address']['streetname'],
                                     Number=store['address']['streetnumber'],
                                     Amount=store['stockInfo']['stockLevel'])
            stores_summarized_data.append(store_data)

        most_availability_store = max(stores_summarized_data, key=lambda store: int(store.Amount))
        stores_summarized_data = [__get_store_tuple_text_summary(t) for t in stores_summarized_data]
        item['storage_data'] = '\n'.join(stores_summarized_data)
        item['most_availability_store'] = most_availability_store.Name
        yield item