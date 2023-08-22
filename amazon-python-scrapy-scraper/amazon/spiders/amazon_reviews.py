import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.crawler  import CrawlerProcess, CrawlerRunner
import fake_useragent
from urllib.parse import urljoin
import pandas as pd
import mysql.connector
from scrapy.utils.project import get_project_settings
from scrapy.item import Item, Field
import re
from twisted.internet import reactor
import datetime
from amazon.analysis_pipeline import fetch_product, create_and_upload_wordclouds, create_and_upload_sentiment_model, remove_duplicate_reviews
import logging


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

class AmazonReviewsSpider(scrapy.Spider):
    name = "amazon_reviews"

    def __init__(self, asin=None, *args, **kwargs):
        super(AmazonReviewsSpider, self).__init__(*args, **kwargs)

        ## take in arguemnt for asin of product to scrape
        self.asin = asin

    max_pages = 200

    current_sort = 0

    sorting_options = {
            4: 'sortBy=reviewerType&filterByStar=four_star',
            3: 'sortBy=reviewerType&filterByStar=three_star',
            2: 'sortBy=reviewerType&filterByStar=two_star',
            1: 'sortBy=reviewerType&filterByStar=one_star',
            5: 'sortBy=reviewerType&filterByStar=five_star',
            6: 'sortBy=recent&filterByStar=one_star',
            7: 'sortBy=recent&filterByStar=two_star',
            8: 'sortBy=recent&filterByStar=three_star',
            9: 'sortBy=recent&filterByStar=four_star',
            10: 'sortBy=recent&filterByStar=five_star'

            

            # Add more sorting options if needed
        }


    def start_requests(self):
        asin_list = [self.asin]

        ua = fake_useragent.UserAgent()
        headers = {'User-Agent': ua.random}

        for asin in asin_list:
            amazon_reviews_url = f'https://www.amazon.com/product-reviews/{asin}/'
            yield scrapy.Request(url=amazon_reviews_url, headers=headers, callback=self.parse_reviews,
                                  meta={'asin': asin, 'retry_count': 0, 'total_pages': 0}
                                  )


    def parse_reviews(self, response):
        asin = response.meta['asin']
        retry_count = response.meta['retry_count']
        total_pages = response.meta["total_pages"]

        ua = fake_useragent.UserAgent()
        headers = {'User-Agent': ua.random}

        self.logger.info(response)

        next_page_relative_url = response.css(".a-pagination .a-last>a::attr(href)").get()
        self.logger.info(f'Spider on url https://www.amazon.com/{next_page_relative_url}')

        if next_page_relative_url is not None:

            self.logger.info(f'Spider on page {total_pages}')
            

            total_pages += 1
            retry_count = 0
            next_page = urljoin('https://www.amazon.com/', next_page_relative_url)
            yield scrapy.Request(url=next_page, headers=headers, callback=self.parse_reviews,
                                meta={'asin': asin, 'retry_count': retry_count, 'total_pages': total_pages}
                                )

        ## Adding this retry_count here so we retry any amazon js rendered review pages
        elif retry_count < 3:
            retry_count = retry_count+1
            yield scrapy.Request(url=response.url, headers=headers, callback=self.parse_reviews,
                                  dont_filter=True, meta={'asin': asin, 'retry_count': retry_count, 'total_pages': total_pages}
                                  )


        # after 10 pages amazon disables next page of reviews
        # work around: sort by stars after these 10 pages get ~100 extra reviews pper new sort
        elif self.current_sort < 2:
            self.current_sort += 1
            # get url for sorted reviews to get extra reviews
            url_stars_sorted = f'https://www.amazon.com/product-reviews/{asin}/?{self.sorting_options[self.current_sort]}'

            yield scrapy.Request(url=url_stars_sorted, headers=headers, callback=self.parse_reviews,
                                  dont_filter=True, meta={'asin': asin, 'retry_count': retry_count, 'total_pages': total_pages}
                                  )
        ## Parse Product Reviews
        review_elements = response.css("#cm_cr-review_list div.review")

        
        for review_element in review_elements:
            review = AmazonReviewItem()
            review["asin"] = asin
            review["text"] = "".join(review_element.css("span[data-hook=review-body] ::text").getall()).strip()
            review["title"] = review_element.css("*[data-hook=review-title]>span::text").get()

            # parsing loc and date
            loc_and_date = review_element.css("span[data-hook=review-date] ::text").get()

            # Extract location using regex
            location_match = re.search(r"Reviewed in (.*?) on", loc_and_date)

            if location_match:
                location = location_match.group(1).strip()
                review["location"] = location
            else:
                review["location"] = "None"

            # Extract date using regex
            date_match = re.search(r"on (\w+ \d+, \d{4})", loc_and_date)

            if date_match:
                date = date_match.group(1).strip()
                # Convert the date string to a datetime object
                date_obj = datetime.datetime.strptime(date, "%B %d, %Y").date()


                review["date"] = date_obj
            else:
                review["date"] = datetime.date(1900, 1, 1)


            # extract verified bool and rating
            review["verified"] = bool(review_element.css("span[data-hook=avp-badge] ::text").get())
            review["rating"] = review_element.css("*[data-hook*=review-star-rating] ::text").re(r"(\d+\.*\d*) out")[0]
            
            




            yield review
            
        
    def closed(self, reason):
        remove_duplicate_reviews(self.asin)
        product_df = fetch_product(asin=self.asin)
        self.logger.info(f"Product df has {len(product_df)} reviews")
        create_and_upload_wordclouds(product_df, self.asin)
        create_and_upload_sentiment_model(product_df, self.asin)
    
def process_scrape_request(asin):
    settings = get_project_settings()
    process = CrawlerRunner(settings)

    process.crawl(AmazonReviewsSpider, asin=asin)
    reactor.run()

def run_scrapy_scraper(asin):
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(AmazonReviewsSpider, asin=asin)
    process.start()

if __name__ == "__main__":

    settings = get_project_settings()
    process = CrawlerRunner(settings)

    spider = AmazonReviewsSpider()
    process.crawl(AmazonReviewsSpider, asin="B0B2VRF2W9")
    reactor.run()