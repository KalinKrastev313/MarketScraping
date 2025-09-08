# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class Product(Item):
    title = Field()
    url = Field()
    price = Field()
    rating = Field()
    images = Field()
    table_values = Field()
    storage_data = Field()
    most_availability_store = Field()