import scrapy
import re


class BrspiderSpider(scrapy.Spider):
    name = "brspider"
    allowed_domains = ["mr-bricolage.bg"]
    start_urls = ["https://mr-bricolage.bg/instrumenti/elektroprenosimi-instrumenti/vintoverti/c/006003013"]
    counter = 0

    def parse(self, response):
        yield from self.parse_search_results_page(response)
        # for page_number in range(1, 8):
        #     next_page_url = self.start_urls[0] + '?currentPage=' + str(page_number)
        #     yield response.follow(next_page_url, callback=self.parse_search_results_page)
        # if self.counter == 1:
        # import pdb; pdb.set_trace()
        # self.counter += 1
        # if next_page_url:
        #     yield response.follow(next_page_url, callback=self.parse)

    def parse_search_results_page(self, response):
        products = response.css(".product__title")

        for product in products:
            self.counter += 1
            if self.counter == 20:
                break
            relative_url = product.css("a::attr(href)").get()
            yield response.follow(relative_url, callback=self.parse_product_page)
            # self.parse_product_page(response, relative_url)
            # yield {
            #     "title": product.css("a::text").get(),
            #     "url": relative_url
            # }

    def parse_product_page(self, response):
        # import pdb; pdb.set_trace()

        title = response.css("brico-pdp-title h1::text").get()
        image_dict = self.get_images_urls_dict(response)
        table_values = self.extract_table_data(response)
        price = self.get_price(response)
        rating = response.css(".rating-count::text").get()

        title = self.ensure_brand_in_the_title(title, table_values)
        product_code = re.search(r"\d+$", response.url).group()
        storage_data = self.get_stores_storage(product_code)


        yield {
            "title": title,
            "url": response.url,
            "price": price,
            "rating": rating,
            **image_dict,
            **table_values,
            "storage_data": self.get_stores_storage(product_code)
        }

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

    def get_stores_storage(self, product_code):


        api_url = f"https://api.mr-bricolage.bg/occ/v2/bricolage-spa/products/{product_code}/stock?fields=stores(name,displayName,address(streetname,streetnumber,town),stockInfo(FULL))&longitude=0&latitude=0"

        # import pdb; pdb.set_trace()
        yield scrapy.Request(
            url=api_url,
            callback=self.__parse_storage_data_json
        )

    def __parse_storage_data_json(self, response):
        data = response.json()
        import pdb; pdb.set_trace()
        return data