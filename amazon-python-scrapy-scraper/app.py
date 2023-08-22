import sys
sys.path.append('./')


from flask import Flask, request, jsonify
# from amazon_reviews import process_scrape_request, AmazonReviewsSpider
from amazon.spiders.amazon_reviews import AmazonReviewsSpider
from flask import Flask, request
from threading import Thread
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.signalmanager import dispatcher
from twisted.internet import reactor
from scrapy import signals
import boto3
import json
from amazon.mysecrets import secrets
import mysql.connector

## imports for celery -- task queue
from celery import Celery
from celery import group
from celery.utils.log import get_task_logger

from amazon.analysis_pipeline import fetch_product, create_and_upload_wordclouds, create_and_upload_sentiment_model

import crochet
crochet.setup()

# for logging
import logging


app = Flask(__name__)

## configuration for celery task queue
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'

logger = get_task_logger(__name__)

# Set up logging for Flask app
app_logger = logging.getLogger('flask_app')
app_logger.setLevel(logging.DEBUG)

# setting up client for aws
lambda_client = boto3.client('lambda', region_name='us-west-1')

project_settings = get_project_settings()
crawler = CrawlerRunner(settings=project_settings)

stop_flag = False


def run_spider(asin):
    global stop_flag
    spider = AmazonReviewsSpider  # Pass the argument to the spider constructor
    crawler.crawl(spider, asin=asin)
    stop_flag = True

    app_logger.debug('Spider run debug message')
    
    if not reactor.running:
        reactor.run()


@app.route('/')
def home():
    return 'Home'

@app.route('/api/test', methods=['GET'])
def test():
    return "API reached!"


@app.route('/api/start', methods=['PUT'])
def start_spider():
    asin = request.json['asin']  # Get the asin from the API request
    Thread(target=run_spider, args=(asin,)).start() # Pass the asin as an argument to run_spider
    app_logger.debug('Started running spider')

    return jsonify({'status': 'success', 'message': 'Spider "amazon_reviews" added to the queue.'}), 202

@app.route('/api/stop', methods=['POST'])
def stop_spider():
    reactor.stop()
    crawler.stop()
    stop_flag = False
    app_logger.debug('Spider stopped in stop API endpoint')
    return 'Spider stopped'
    
@app.route('/api/wordclouds', methods=['PUT'])
def wordclouds():
    asin = request.json['asin']  # Get the asin from the API request

    product_df = fetch_product(asin=asin)
    create_and_upload_wordclouds(product_df, asin=asin)
    return "Started creating and uploading wordclouds"

@app.route('/api/sentiment-model', methods=['PUT'])
def sentiment_model():
    asin = request.json['asin']  # Get the asin from the API request

    product_df = fetch_product(asin=asin)

    # Impute positive or negative based on the 'rating' column
    product_df['sentiment'] = product_df['rating'].apply(lambda x: 'positive' if x >= 4 else 'negative')

    if product_df["sentiment"].nunique() < 2:
        return "Only one class of sentiment for this products model - all positive or all negative so\
            I can't make a model"

    create_and_upload_sentiment_model(product_df, asin=asin)
    return "Started creating and uploading sentiment model important words"


## request to add product info to the db
def get_mysql_connection():
    connection = mysql.connector.connect(
        host=secrets.get("DB_HOST"),
        user=secrets.get("DB_USER"),
        password=secrets.get("DB_PASSWORD"),
        database=secrets.get("DATABASE")
    )
    return connection

@app.route('/api/add_product', methods=['POST'])
def add_product():
    try:
        # Parse the JSON data from the request
        data = request.get_json()
        table_name = 'product_names'
        id_column = 'id'
        asin_column = 'asin'
        words_to_exclude_column = 'words_to_exclude'
        interested_words_column = 'interested_words'
        product_name_column = 'product_name'

        # Create the table if it doesn't exist
        connection = get_mysql_connection()
        cursor = connection.cursor()
        create_table_query = f'''CREATE TABLE IF NOT EXISTS {table_name} (
            {id_column} INT AUTO_INCREMENT PRIMARY KEY,
            {asin_column} VARCHAR(255) NOT NULL,
            {words_to_exclude_column} VARCHAR(255) NOT NULL,
            {interested_words_column} VARCHAR(255) NOT NULL,
            {product_name_column} VARCHAR(255) NOT NULL
        )'''
        cursor.execute(create_table_query)

        # Insert a row with the data from the JSON request
        insert_query = f'''INSERT INTO {table_name} ({asin_column}, {words_to_exclude_column}, {interested_words_column}, {product_name_column})
                           VALUES (%s, %s, %s, %s)'''
        values = (data[asin_column], data[words_to_exclude_column], data[interested_words_column], data[product_name_column])
        cursor.execute(insert_query, values)

        connection.commit()
        cursor.close()
        connection.close()

        return 'Table created and row inserted successfully'
    except Exception as e:
        return str(e), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
