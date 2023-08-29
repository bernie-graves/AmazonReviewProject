# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


import mysql.connector

class DatabasePipeline:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None

        self.conn = mysql.connector.connect(
            host = host,
            user = user,
            password = password,
            database = database
        )

        ## Create cursor, used to execute commands
        self.cur = self.conn.cursor()
        
        ## Create quotes table if none exists
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews(
            id int NOT NULL auto_increment, 
            asin text,
            text text,
            title text,
            location text,
            date date,
            verified bool, 
            rating int,
            PRIMARY KEY (id)
        )
        """)

                ## Create quotes table if none exists
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id int NOT NULL auto_increment, 
            asin text,
            words_to_exclude text,
            interested_words text,
            PRIMARY KEY (id)
        )
        """)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        host = settings.get('MYSQL_HOST')
        port = settings.get('MYSQL_PORT')
        database = settings.get('MYSQL_DATABASE')
        user = "admin"
        password = settings.get('MYSQL_PASSWORD')
        return cls(host, port, database, user, password)

    def open_spider(self, spider):
        self.conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
        self.cursor = self.conn.cursor()

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):

        
        # Adapt this code to match your item structure and database table
        query = "INSERT INTO reviews (asin, text, title, location, date, verified, rating) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (item['asin'], item['text'], item['title'], item['location'], item['date'].strftime('%Y-%m-%d'), item['verified'], item['rating'])
        self.cursor.execute(query, values)
        self.conn.commit()
        return item


# from scrapy.exceptions import CloseSpider
# from twisted.internet import reactor


# class StopAfterCountPipeline:
#     def __init__(self, count):
#         self.count = count
#         self.item_count = 0

#     @classmethod
#     def from_crawler(cls, crawler):
#         count = crawler.settings.getint('STOP_AFTER_COUNT')
#         return cls(count)

#     def process_item(self, item, spider):
#         self.item_count += 1
#         if self.item_count >= self.count:
#             raise CloseSpider(f"Reached item count: {self.item_count}")
#         return item
