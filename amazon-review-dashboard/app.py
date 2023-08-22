import pandas as pd
import plotly.express as px
import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

import re
import requests

# for importing images from aws
import boto3
from PIL import Image
from io import BytesIO

# for connecting to mySQL db
from mysecrets import secrets
import mysql.connector

def get_mysql_connection():
    connection = mysql.connector.connect(
        host=secrets.get("DB_HOST"),
        user=secrets.get("DB_USER"),
        password=secrets.get("DB_PASSWORD"),
        database=secrets.get("DATABASE")
    )
    return connection

# function to grab the wordclouds from the bucket
def fetch_wordclouds(asin_to_fetch):

    # Create a Boto3 S3 client
    s3_client = boto3.client('s3', region_name='us-west-1')

    # Specify the S3 bucket name
    bucket_name = 'amazon-product-analysis-objects'

    # Fetch the image URLs for the specified ASIN
    neg_image_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': f'negative_word_cloud_{asin_to_fetch}.png'
        },
        ExpiresIn=3600  # URL expiration time in seconds (e.g., 1 hour)
    )

    pos_image_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': f'positive_word_cloud_{asin_to_fetch}.png'
        },
        ExpiresIn=3600  # URL expiration time in seconds (e.g., 1 hour)
    )
    return [neg_image_url, pos_image_url]

# function to grab important words from the s3 bucket
def fetch_important_words_csv(asin):
    # Create a Boto3 S3 client
    s3_client = boto3.client('s3', region_name='us-west-1')

    # Specify the S3 bucket name
    bucket_name = 'amazon-product-analysis-objects'

    # Specify the CSV file name based on the ASIN
    file_name = f'important_words_{asin}.csv'

    try:
        # Fetch the CSV file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_name)

        # Read the CSV file using pandas
        df = pd.read_csv(response['Body'])

        return df

    except Exception as e:
        print(f"Error fetching important words CSV for ASIN {asin}: {str(e)}")
        return None
    
# function to fetch reviews withg certain asin
def fetch_reviews(asin):
    # Establish a connection to your MySQL database
    conn = get_mysql_connection()

    try:
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()

        # Define the SQL query to fetch reviews for the specified ASIN
        query = f"SELECT * FROM reviews WHERE asin = '{asin}'"

        # Execute the SQL query
        cursor.execute(query)

        # Fetch all the reviews
        reviews = cursor.fetchall()

        # Get the column names from the cursor description
        column_names = [desc[0] for desc in cursor.description]

        # Create a pandas DataFrame from the fetched reviews
        df = pd.DataFrame(reviews, columns=column_names)

        return df

    except mysql.connector.Error as e:
        print(f"Error fetching reviews for ASIN {asin}: {str(e)}")
        return None

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def create_ratings_plot(df):
    
    df['date'] = pd.to_datetime(df['date'])

    # Extract month and year for grouping
    df['month'] = df['date'].dt.strftime('%Y-%m')

    # Group the data by month and rating
    grouped = df.groupby(['month', 'rating']).size().reset_index(name='count')

    # Create the line graph
    fig = px.line(grouped, x='month', y='count', color='rating',
                labels={'month': 'Month', 'count': 'Number of Ratings'},
                title='Number of Ratings by Month and Rating')
    
    return fig


# get all the unique product ASIN values
db = get_mysql_connection()

# Create a cursor object to execute MySQL queries
cursor = db.cursor()

# Execute the SQL query to retrieve asin and product_name columns
query = "SELECT asin, product_name FROM product_names"
cursor.execute(query)

# Fetch all the results
results = cursor.fetchall()

# Extract the product names from the results
product_names = [result[1] for result in results]
asins = [result[0] for result in results]

# Close the cursor and database connection
cursor.close()
db.close()

image_urls = fetch_wordclouds(asin_to_fetch="B0B2VRF2W9")

# Custom circular component to display number of products reviews
def CircularComponent(value):
    return html.Div([
        html.Div(f"{value}", className="circle-text"),
    ], className="circle")



# Create the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Amazon Reviews Dashboard'

# Define the layout of the app
app.layout = html.Div(
    style={'padding': '20px', 'justify-content': 'center'},
    children = [

    html.H1("Amazon Review Dashboard",
            style={'text-align': 'center'}),

    dcc.Dropdown(
        id='product-dropdown',
        options=[{'label': product_name, 'value': asin} for product_name, asin in zip(product_names, asins)],
        placeholder='Select a product',
        style={'color': 'black', 'padding-left': "20px", 'padding-right': "20px"}
    ),

    dbc.Button('New Product', id='open-button', n_clicks=0),

# form to request new product
 dbc.Modal([
        dbc.ModalHeader('Form'),
        dbc.ModalBody([
            dbc.CardGroup([
                dbc.Label('ASIN'),
                dbc.Input(id='input-asin', type='text', placeholder='Enter ASIN', maxLength=10, pattern=r'[A-Za-z0-9]{1,10}')
            ]),
            dbc.CardGroup([
                dbc.Label('Product Name'),
                dbc.Input(id='input-product-name', type='text', placeholder='Enter Product Name or Nickname')
            ]),
            dbc.CardGroup([
                dbc.Label('Words to Exclude'),
                dbc.Input(id='input-words-to-exclude', type='text', placeholder='Enter words to exclude')
            ]),
            dbc.CardGroup([
                dbc.Label('Interested Words  - word1,word2, word3...'),
                dbc.Input(id='input-interested-words', type='text', placeholder='Enter interested words')
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button('Submit', id='submit-button', n_clicks=0),
            dbc.Button('Close', id='close-button', n_clicks=0, className='ml-auto')
        ])
    ], id='form-modal', centered=True, is_open=False),
    html.Div(id='output-container'),

    # div to display what product is selected
    html.Div(id='selected-product'),

    dbc.Row([
        # First Column: Wordclouds
        dbc.Col(html.Div("Wordclouds", id="wordclouds"), width=6),
        # Second Column: Important Words and Ratings Graph
        dbc.Col([
            html.Div("Review-Count", id="review-count",
                      style={'justify-content': 'center',
                                 'display':'flex'}),
            html.Div("Important Words", id="important-words",
                     style={'justify-content': 'center',
                                 'display':'flex'}  ),
            html.Div("Ratings Graph", id="ratings-graph"),
        ], width=6),
    ]),
])

# callback to show the new product form
@app.callback(
    Output('form-modal', 'is_open'),
    [Input('open-button', 'n_clicks'),
     Input('close-button', 'n_clicks'),
     Input('submit-button', 'n_clicks')],
    [State('form-modal', 'is_open')]
)
def toggle_form_modal(open_clicks, close_clicks, submit_clicks, is_open):
    if open_clicks or close_clicks:
        return not is_open
    elif submit_clicks:
        return False
    return is_open



# Define the callback to display the selected product
@app.callback(
    Output('selected-product', 'children'),
    [Input('product-dropdown', 'value')]
)
def display_selected_product(selected_product):
    if selected_product:
        return html.H3(f'Selected Product: {selected_product}')
    else:
        return html.Div()

# Define the callback to update the wordclouds
@app.callback(
    Output('wordclouds', 'children'),
    [Input('product-dropdown', 'value')]
)
def update_wordclouds(asin):
    if asin:
        # Fetch the wordclouds for the selected ASIN
        image_urls = fetch_wordclouds(asin_to_fetch=asin)

        # Create a list of image components
        image_components = [html.Div([
                                dcc.Loading(
                                    html.Img(src=image_url)
                                    )], style={'margin-bottom': '20px'}
                                ) for image_url in image_urls]

        # Return the image components
        return image_components
    else:
        return html.Div()
    

# Define the callback to update the wordclouds
@app.callback(
    Output('important-words', 'children'),
    [Input('product-dropdown', 'value')]
)
def update_important_words(asin):
    if asin:
        # Fetch the wordclouds for the selected ASIN
        important_words_df = fetch_important_words_csv(asin=asin)
        

        if isinstance(important_words_df, pd.DataFrame):
            colored_words_table =  html.Table([
                html.Thead(html.Tr([html.Th('Word'), html.Th('Importance')])),
                html.Tbody([
                    html.Tr(
                        [
                            html.Td(word),
                            html.Td(importance, style={'color': 'green' if importance > 0 else 'red'})
                        ]
                    ) for word, importance in zip(important_words_df['feature'], important_words_df['coefficient'])
                ])
            ]),

            return colored_words_table
        else:
            # returns when asin exists but important words df couldn't get made
            # they can't get made when too few reviews
            return html.Div(
                html.H3("Important words df doesn't exist for this product. Might need to scrape more reviews for it.")
            )
    else:
        return html.Div()
    

# Define the callback to update the ratings graph and review count
@app.callback(
    [Output('ratings-graph', 'children'),
     Output('review-count', 'children')],
    [Input('product-dropdown', 'value')]
)   
def update_ratings_graph(asin):
    reviews_df = fetch_reviews(asin=asin)

    fig = create_ratings_plot(reviews_df)
    graph = html.Div([
        html.H2('Number of Ratings by Date Bin'),
        dcc.Graph(id='rating-counts-plot', figure=fig)
    ])

    review_count_display = CircularComponent(len(reviews_df))
    return graph, review_count_display


# callback to submit form - makes request to backend api
@app.callback(
    Output('output-container', 'children'),
    [Input('submit-button', 'n_clicks')],
    [State('input-asin', 'value'),
     State('input-words-to-exclude', 'value'),
     State('input-interested-words', 'value'),
     State('input-product-name', 'value')]
)
def submit_form(n_clicks, asin_value, words_to_exclude, interested_words, product_name):
    if n_clicks > 0:
        if not asin_value or not re.match(r'^[A-Z0-9]{10}$', asin_value):
            return html.Div([
                html.H3('Form Submission'),
                html.P('Invalid ASIN. Please enter a valid ASIN (10 characters, no spaces or special characters).')
            ])

        # Make a request to the Flask API to add the data to the MySQL database
        add_product_url = 'http://localhost:5000/api/add_product'
        product_data = {
            'asin': asin_value,
            'product_name': product_name,
            'words_to_exclude': words_to_exclude,
            'interested_words': interested_words,

        }
        product_response = requests.post(add_product_url, json=product_data)
        

        # Make a PUT request to the api URL with JSON data to start scraping 
        start_scrape_url = 'http://127.0.0.1:5000/api/start'
        start_data = {'asin': asin_value}
        start_response = requests.put(start_scrape_url, json=start_data)

        if product_response.status_code == 200 and start_response.status_code == 200:
            return html.Div([
                html.H3('Form Submission'),
                html.P('Data successfully added to the database and scraping started.')
            ])
        elif product_response.status_code == 200 and start_response.status_code != 200:
            return html.Div([
                html.H3('Form Submission'),
                html.P('Data successfully added to the database but scraping failed to start.')
            ])
        elif product_response.status_code != 200 and start_response.status_code == 200:
            return html.Div([
                html.H3('Form Submission'),
                html.P('Data unsuccessfully added to the database but scraping started.')
            ])
        else:
            return html.Div([
                html.H3('Form Submission'),
                html.P('Error occurred while adding data to the database and scraping could not start.')
            ])
    else:
        return html.Div()

# Callback to automatically uppercase ASIN
@app.callback(
    Output('input-asin', 'value'),
    [Input('input-asin', 'value')]
)
def update_asin_value(value):
    if value is not None:
        return value.upper()

    return ''

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)



### old code for reference


# df = pd.read_json("../reviews_both.json")

# # Extract 'location' and 'date' from 'location_and_date'
# df['location'] = df['location_and_date'].str.extract('Reviewed in (\D+)')
# df['date'] = df['location_and_date'].str.extract('on (\w+ \d+, \d+)')
# df['date'] = pd.to_datetime(df['date'])


# # Impute positive or negative based on the 'rating' column
# df['sentiment'] = df['rating'].apply(lambda x: 'positive' if x >= 4 else 'negative')


# magnetic_charger = df[df["asin"] == "B0BPR6FL7M"]
# ab_charger = df[df["asin"] == "B01GGKYKQM"]


# # Define the time intervals for binning
# bins = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='M')

# # Bin the dates into specific time intervals
# df['date_bin'] = pd.cut(df['date'], bins=bins, labels=bins[:-1])

# # Group the data by 'date_bin' and 'rating' and count the occurrences
# grouped = df.groupby(['date_bin', 'rating']).size().unstack(fill_value=0)

# # Reset index and convert the date_bin column back to datetime
# grouped = grouped.reset_index()
# grouped['date_bin'] = pd.to_datetime(grouped['date_bin'])

# # Plot the data using Plotly
# fig = px.line(grouped, x='date_bin', y=[1, 2, 3, 4, 5],
#               labels={'value': 'Count', 'date_bin': 'Date Bin'},
#               title='Number of Ratings by Date Bin')

    # html.Table([
    #     html.Thead(html.Tr([html.Th('Word'), html.Th('Importance')])),
    #     html.Tbody([
    #         html.Tr(
    #             [
    #                 html.Td(word),
    #                 html.Td(importance, style={'color': 'green' if importance > 0 else 'red'})
    #             ]
    #         ) for word, importance in zip(word_importances['feature'], word_importances['coefficient'])
    #     ])
    # ]),
    # html.Div([
    #     html.H2('Number of Ratings by Date Bin'),
    #     dcc.Graph(id='rating-counts-plot', figure=fig)
    # ]),