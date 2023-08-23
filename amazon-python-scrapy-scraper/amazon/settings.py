import logging
import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = 'amazon'

SPIDER_MODULES = ['amazon.spiders']
NEWSPIDER_MODULE = 'amazon.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

SCRAPEOPS_API_KEY = os.getenv("SCRAPE_OPS_API_KEY")

SCRAPEOPS_PROXY_ENABLED = True
SCRAPEOPS_PROXY_SETTINGS = {'country': 'us'}

# Add In The ScrapeOps Monitoring Extension
EXTENSIONS = {
'scrapeops_scrapy.extension.ScrapeOpsMonitor': 500, 
}

LOG_LEVEL = 'INFO'

DOWNLOADER_MIDDLEWARES = {

    ## ScrapeOps Monitor
    'scrapeops_scrapy.middleware.retry.RetryMiddleware': 550,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    
    ## Proxy Middleware
    'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,

    # Enable Scrapy-Fake-UserAgent
    # 'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    # 'scrapy_fake_useragent.middleware.RandomUserAgentMiddleware': 400,    
}

# Max Concurrency On ScrapeOps Proxy Free Plan is 1 thread
CONCURRENT_REQUESTS = 1

# MySQL database settings
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = 3306
MYSQL_DATABASE = 'reviews_db'
MYSQL_USER = 'admin'
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

ITEM_PIPELINES = {
    'amazon.pipelines.DatabasePipeline': 300,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'


HTTPERROR_ALLOWED_CODES  =[404]

# logging settings
LOG_ENABLED = True
LOG_LEVEL = logging.DEBUG


