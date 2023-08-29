# Amazon Review Scraper and Dashboard

A dashboard and scraping web app made for Amazon sellers to quickly identify products to sell and features to market.

<details>
<summary>Table of Contents</summary>

- [Project Overview](#project-overview)
- [Quickstart Guide](#quickstart-guide)
  - [Windows](#windows-setup)
  - [MacOS/Linux](#macos-and-linux-setup)
- [More Details](#more-details)
- [Credits](#credits)

</details>

## Project Overview

This app consists of two main pieces. The frontend dashboard built with the Python library Dash and a backend REST API built with flask

### The Frontend

![screenshot of dashboard](assets/amazon-review-dashboard.png)

The dashboard displays feature importances from a sentiment model trained on the selected product's reviews. This tells us which words are specifically contributing to a review being classified as negative or positive. It also features graphics to display the number of reviews scraped for this product and the number of reviews over time grouped by the rating. The bottom half of the dashboard shows two wordclouds created by subsetting the data by positive and negative reviews. The larger the word, the more prevalent it is in those type of reviews. Combined, these figures help to identify pain points and pleasure points in the selected product.

The frontend also features buttons which make it easy to request a new product to be scraped or to scrape additional reviews for the selected product. by submitting these forms, you make a request to the backend REST API that starts a scraping task.

![screenshot of scrape form](assets/scrape-request-form.png)

### The Backend

The backend is a REST API created with Flask. Its most important endpoint is used to start a web scraper that scrapes Amazon product reviews for the requested product. The scraper features a pipeline that parses and sends the data to a MySQL database table. When the scraping is completed, another pipeline is triggered that creates the wordclouds and sentiment models for the selected product and pushes the results to an AWS S3 bucket.

## Quickstart Guide

Before starting, clone the repository locally.

### 1.) Database Setup

The first step is to setup a MySQL database. Note the database name, host, the mmaster user, the password. I used AWS RDS to host mine (see setup [here](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Tutorials.WebServerDB.CreateDBInstance.html)) but a locally hosted MySQL database should work too. If using AWS RDS, make sure to set `Publically accessible` to Yes.

### 2.) AWS S3 Bucket Setup

You will need to setup an AWS S3 bucket to hold the wordclouds and the results from the sentiment model. You can see a guide [here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/creating-bucket.html). Make sure to name the bucket `amazon-product-analysis-objects` and make objects can be public. Also note the regions the bucket is in, your AWS Access Key and AWS Secret Access Key. For help with this go [here](https://aws.amazon.com/blogs/security/wheres-my-secret-access-key/).

### 3.) Scrapeops Setup

Next, you need to setup an account with Scrapeops. The scraper is built with their package Scrapy and they provide a proxy service for scraping. There free tier allows 1000 pages to be scraped which should be good for a decent amount of products but you can upgrade to a paid plan if needed. Sign up for an account [here](https://scrapeops.io/app/register/main) and find the Account API Key in the Settings tab.

### 4.) Secrets Configuration

You will need to create 2 files to keep passwords and secrets hidden. One will use a `.env` file to store database information and the other will be a python file called `mysecrets.py`. Both are in the `.gitignore` file and will be ignored by source control and keeps them relatively secure.

You will create the `.env` file in the `amazon-python-scrapy-scraper/` directory and fill in the following replacing with your secrets:

```env
# amazon-python-scrapy-scraper/.env

SCRAPE_OPS_API_KEY='scrapeops_api_key'

# database secrets-
MYSQL_HOST='mysql_database_host'
MSQL_DATABASE='mysql_database_name'
MYSQL_PASSWORD='mysql_database_password'


# aws keys
AWS_ACCESS_KEY_ID=aws_access_key
AWS_DEFAULT_REGION=aws_region
AWS_SECRET_ACCESS_KEY=aws_secret_access_key
```

Create `mysecrets.py` in the `amazon-reviews-dashboard/` directory and replace with your secrets.

```python
# amazon-python-dashboard/mysecrets.py

secrets = {
    'DB_PASSWORD': 'MySQL_Password',
    'DB_HOST': 'MySQL_Database_Host',
    'DB_PORT': 3306,
    'DB_USER': "admin",
    'DATABASE': "MySQL_database_name",
    'AWS_BUCKET_REGION': 'AWS_bucket_region',
    'AWS_BUCKET_NAME': "AWS_bucket_name",
    'AWS_ACCESS_KEY': "AWS_access_key",
    'AWS_SECRET_ACCESS_KEY': "AWS_secret_access_key"
}

```

# REAL ONENNNNNN

### Windows Startup

Windows quickstart

### MacOS and Linux Startup

linux setup

## More Details

Provide more in-depth information about your project...

## Credits

Acknowledge and give credit to contributors...
