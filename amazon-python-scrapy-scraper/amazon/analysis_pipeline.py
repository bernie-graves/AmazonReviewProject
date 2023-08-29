import mysql.connector
import pandas as pd
from wordcloud import WordCloud, STOPWORDS
import boto3
from io import BytesIO
from PIL import Image
import io

# secrets
from dotenv import load_dotenv
import os

load_dotenv()

# for sentiment model
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import LogisticRegression
import nltk

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Download required NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')



def remove_duplicate_reviews(asin):

    # Connect to mySQL db
    db_config = {
        'user': os.getenv("MYSQL_USER"),
        'password': os.getenv("MYSQL_PASSWORD"),
        'host': os.getenv("MYSQL_HOST"),
        'port': 3306,
        'database': os.getenv("MSQL_DATABASE"),
    }

    conn = mysql.connector.connect(**db_config)
    asin_value = asin

    # # Create a temporary table for duplicate texts
    # create_temp_table_query = f"""CREATE TEMPORARY TABLE temp_duplicate_texts AS
    #                              SELECT text
    #                              FROM reviews
    #                              WHERE asin = '{asin_value}'
    #                              GROUP BY text
    #                              HAVING COUNT(*) > 1;"""

    # # Delete records using the temporary table
    # delete_query = """DELETE FROM reviews
    #                   WHERE text IN (SELECT text FROM temp_duplicate_texts);"""

    # # Drop the temporary table
    # drop_temp_table_query = "DROP TEMPORARY TABLE IF EXISTS temp_duplicate_texts;"

    # remove duplicates 
    remove_duplicates_query = """DELETE S1 FROM reviews AS S1  
                                INNER JOIN reviews AS S2   
                                WHERE S1.id < S2.id AND S1.text = S2.text 
                                AND S1.asin = S2.asin; """


    cursor = conn.cursor()

    cursor.execute(remove_duplicates_query)
        
    # Commit the changes to the database
    conn.commit()

    # Close the cursor
    cursor.close()


def fetch_product(asin):

    # Connect to mySQL db
    db_config = {
        'user': os.getenv("MYSQL_USER"),
        'password': os.getenv("MYSQL_PASSWORD"),
        'host': os.getenv("MYSQL_HOST"),
        'port': 3306,
        'database': os.getenv("MSQL_DATABASE"),
    }

    conn = mysql.connector.connect(**db_config)

    # Select the product from the db
    asin_value = asin

    query = f"SELECT * FROM reviews WHERE asin = '{asin_value}'"

    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()

    # put into pandas df for analysis
    df = pd.DataFrame(results, columns=cursor.column_names)
    return df


def create_and_upload_wordclouds(df, asin):
    # Create stopword list:
    stopwords = set(STOPWORDS)




    # Specify the S3 bucket name
    bucket_name = 'amazon-product-analysis-objects'
    # Create a Boto3 S3 client
    s3 = boto3.resource('s3')

    # Create Positive Wordcloud
    positive_reviews = df[df["rating"] > 3]
    print(len(positive_reviews))
    positive_reviews_text = " ".join(review for review in positive_reviews["text"])

    # If there are positive reviews - create and upload wordcloud
    if len(positive_reviews) > 0:
        print("started_positive wordcloud")
        # Create and generate a word cloud image:
        pos_wordcloud = WordCloud(stopwords=stopwords, background_color="white", width=800, height=600).generate(positive_reviews_text)

        pos_image_key = f'positive_word_cloud_{asin}.png'

        pos_object = s3.Object(bucket_name, pos_image_key)

        # here you convert the PIL image that generate wordcloud to byte array
        pos_image_byte = image_to_byte_array(pos_wordcloud.to_image())
        pos_object.put(Body=pos_image_byte)


    # Create Negative Wordcloud
    neg_reviews = df[df["rating"] <= 3]
    neg_reviews_text = " ".join(review for review in neg_reviews["text"])

    # If there are negative reviews - create and upload wordcloud
    if len(neg_reviews) > 0:
        # Create and generate a word cloud image:
        neg_wordcloud = WordCloud(stopwords=stopwords, background_color="white", width=800, height=600, colormap="magma").generate(neg_reviews_text)

        neg_image_key = f'negative_word_cloud_{asin}.png'

        neg_object = s3.Object(bucket_name, neg_image_key)

        # here you convert the PIL image that generate wordcloud to byte array
        neg_image_byte = image_to_byte_array(neg_wordcloud.to_image())
        neg_object.put(Body=neg_image_byte)




def image_to_byte_array(image: Image, format: str = 'png'):
    result = io.BytesIO()
    image.save(result, format=format)
    result = result.getvalue()

    return result

# Define the preprocessing functions
def preprocess_text(text):
    # Convert to lowercase
    text = text.lower()

    # Tokenize the text
    tokens = word_tokenize(text)

    # Remove stop words
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]

    # Lemmatize the tokens
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]

    # Join tokens back to a string
    preprocessed_text = ' '.join(tokens)

    return preprocessed_text

## function to create Logistic Regression sentiment analysis model and upload important words to S3
def create_and_upload_sentiment_model(df, asin):

    # Impute positive or negative based on the 'rating' column
    df['sentiment'] = df['rating'].apply(lambda x: 'positive' if x >= 4 else 'negative')

    # Define the pipeline
    pipeline = Pipeline([
        ('preprocess', CountVectorizer(preprocessor=preprocess_text)),
        ('tfidf', TfidfTransformer()),
        ('classifier', LogisticRegression())
    ])

    # Separate the features (preprocessed text) and target variable (sentiment)
    X = df['text']
    y = df['sentiment']

    # Train the pipeline
    pipeline.fit(X, y)
    print("fitted sentiment model")

    # Get the feature names from the CountVectorizer
    feature_names = pipeline.named_steps['preprocess'].get_feature_names_out()

    # Get the coefficients from the trained LogisticRegression classifier
    coefficients = pipeline.named_steps['classifier'].coef_[0]

    # Create a DataFrame with feature names and their corresponding coefficients
    coef_df = pd.DataFrame({'feature': feature_names, 'coefficient': coefficients})

    # Sort the DataFrame by the absolute value of coefficients
    sorted_coef_df = coef_df.reindex(coef_df['coefficient'].abs().sort_values(ascending=False).index)


    # Select the top 15 words with coefficients
    top_15_words_with_coefs = sorted_coef_df.head(15)

    # convert to csv string to put in s3 bucket
    important_words_csv = top_15_words_with_coefs.to_csv()


    # Upload to s3 bucket
    # Specify the S3 bucket name
    bucket_name = 'amazon-product-analysis-objects'
    # Create a Boto3 S3 client
    s3 = boto3.resource('s3')


    key = f'important_words_{asin}.csv'
    object = s3.Object(bucket_name, key)
    object.put(Body=important_words_csv)

    print("Done")


if __name__ == "__main__":

    asin="B01GGKYKQM"
    product_df = fetch_product(asin=asin)
    create_and_upload_sentiment_model(product_df, asin=asin)