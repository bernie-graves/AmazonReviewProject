# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.item import Item, Field

class AmazonReviewItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    asin = Field()
    text = Field()
    title = Field()
    location = Field()
    date = Field()
    verified = Field()
    rating = Field()
