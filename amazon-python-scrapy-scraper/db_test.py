import mysql.connector
from mysql.connector import Error

# config = {
#     'user': 'admin',
#     'password': '#B3rniejr01',
#     'host': 'reviews-db.cawrdqygknxl.us-east-2.rds.amazonaws.com',
#     'database': 'reviews_db',
#     'port': 3306,
# }

# connection = mysql.connector.connect(**config)
# cursor = connection.cursor()

# query = 'SELECT * FROM your_table_name'
# cursor.execute(query)
# result = cursor.fetchall()
# for row in result:
#     print(row)

# cursor.close()
# connection.close()


# def connect():
#     """ Connect to MySQL database """
#     conn = None
#     try:
#         conn = mysql.connector.connect(
#                     host = 'reviews-db.cawrdqygknxl.us-east-2.rds.amazonaws.com',
#                     user = "admin",
#                     password = "#B3rniejr01",
#                     database = "reviews_db"
#                 )
#         if conn.is_connected():
#             print('Connected to MySQL database')

#     except Error as e:
#         print(e)

#     finally:
#         if conn is not None and conn.is_connected():
#             conn.close()


# if __name__ == '__main__':
#     connect()

# for importing images from aws
# import boto3
# from PIL import Image
# from io import BytesIO

# def fetch_wordclouds(asin_to_fetch):
#     dynamodb = boto3.resource('dynamodb')
#     table_name = 'amazon-product-analysis-urls'
#     table = dynamodb.Table(table_name)

#     # Fetch the image URLs for the specified ASIN
#     response = table.get_item(Key={'asin': asin_to_fetch})
#     item = response['Item']

#     asin = item['asin']
#     neg_image_url = item['negative_worldcloud']['image_url']
#     pos_image_url = item['positive_wordcloud']['image_url']
#     return [neg_image_url, pos_image_url]


# DAte formatting
import datetime


date = " July 15, 2023 "

date_obj = datetime.datetime.strptime(date.strip(), "%B %d, %Y").date()

print(date_obj)
