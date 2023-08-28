import pandas as pd
import plotly.express as px
import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dash_table
from dash.dash_table.Format import Format, Scheme

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
    return {"neg_image_url": neg_image_url, "pos_image_url": pos_image_url}

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
                category_orders={'rating': [1, 2, 3, 4, 5]})
    
    return fig

def get_products():
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

    return product_names, asins

product_names, asins = get_products()

# Custom circular component to display number of products reviews
def CircularComponent(value):
    return html.Div([
        
        html.Div(f"{value}", className="circle-text"),
    ], className="circle")



# Create the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])
app.title = 'Amazon Reviews Dashboard'

# Define the layout of the app
app.layout = html.Div(
    style={'padding': '20px', 'justify-content': 'center'},
    children = [
    
    # style sheet
    html.Link(href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css", rel="stylesheet"),

    html.H1("Amazon Review Dashboard",
            style={'text-align': 'center'}),

    dbc.Row([
        dbc.Col([        
                dcc.Dropdown(
                id='product-dropdown',
                options=[{'label': product_name, 'value': asin} for product_name, asin in zip(product_names, asins)],
                placeholder='Select a product',
                style={'color': 'black', 'padding-left': "20px", 'padding-right': "0px"}
            ),], width=9), 

        dbc.Col([
            dbc.Button(html.I(className='bi bi-arrow-clockwise'), id='refresh-button', n_clicks=0, className="me-md-1"),
            dbc.Button('New Product', id='open-button', n_clicks=0, className="me-md-1"),
            dbc.Button('Scrape More', id='scrape-more-button', n_clicks=0, className="me-md-1"),
        ], width=3),
        
    
    ]),


# form to request new product
 dbc.Modal([
        dbc.ModalHeader('Scrape Request Form'),
        dbc.ModalBody([
            dbc.CardGroup([
                dbc.Label('ASIN'),
                dbc.Input(id='input-asin', type='text', placeholder='Enter ASIN', maxLength=10, pattern=r'[A-Za-z0-9]{1,10}')
            ]),
            dbc.CardGroup([
                dbc.Label('Product Name'),
                dbc.Input(id='input-product-name', type='text', placeholder='Enter Product Name or Nickname')
            ])
        ]),
        dbc.ModalFooter([
            dcc.Loading(
                    id="loading-icon",
                    children=[html.Div([html.Div(id="loading-output")])],
                    type="circle",
                    
                ),
            html.Div(id="form-result-message"),
            html.Div(id="form-result-icon", className="", style={"margin-left": "10px"}),
            dbc.Button('Submit', id='submit-button', n_clicks=0),
            dbc.Button('Close', id='close-button', n_clicks=0, className='ml-auto')
        ])
    ], id='form-modal', centered=True, is_open=False),
    html.Div(id='output-container'),

    # div with all of the figures
    html.Div([
        # div to display what product is selected
        html.Div(id='selected-product', style={"margin": '20px'}),

        dbc.Row([

            # First Row: Important Words, Review Count and Ratings Graph
            dbc.Row([

                dbc.Col([
                    html.Div("Important Words", id="important-words",
                        style={'justify-content': 'center',
                                    'display':'flex', 'margin-left': '20px'})
                ], width=4),
                dbc.Col([                
                    html.Div("Review-Count", id="review-count",
                        style={'justify-content': 'center',
                                    'display':'flex'})
                                    ],
                        width = 3, className = 'figure'), 
                dbc.Col([
                    html.Div("Ratings Graph", id="ratings-graph"),
                ], width = 5, style={'margin': '0px'}),

                

            ]),
            # Second Column: Wordclouds
            dbc.Row([
                dbc.Col([
                    html.Div("Positive Wordcloud", id="pos-wordcloud")
                ], width = 6, className='figure'),
                dbc.Col([
                    html.Div("Negative Wordcloud", id="neg-wordcloud")
                ], width = 6, className='figure')
            ]),
        ]),
    ], id="figure-div", style={"display":'none'}),
    
    # div to display something before product is selected
    html.Div([
        html.H3("Select a product or start a scrape request!")
    ], id="home-placeholder", style={'display':'block', 'padding': '20px'})
])



# callback to submit form - makes request to backend api
@app.callback(
    [Output('loading-output', 'className'),
    Output('form-result-icon', 'className'),
    Output('form-result-message', 'children')],
    [Input('submit-button', 'n_clicks')],
    [State('input-asin', 'value'),
     State('input-product-name', 'value')]
)
def submit_form(n_clicks, asin_value, product_name):

    loading_icon_class = ""
    result_icon_class = ""


    if n_clicks > 0:

        # set class names for loading and result icons after submit is clicked
        loading_icon_class = ""
        result_icon_class = ""
        result_message = ""


        if not asin_value or not re.match(r'^[A-Z0-9]{10}$', asin_value):
            result_icon_class = "fas fa-times-circle"
            result_message = 'Enter Valid Asin'
            return loading_icon_class, result_icon_class, result_message

        # Make a request to the Flask API to add the data to the MySQL database
        add_product_url = 'http://localhost:5000/api/add_product'
        product_data = {
            'asin': asin_value,
            'product_name': product_name

        }
        try:
            product_response = requests.post(add_product_url, json=product_data)
            

            # Make a PUT request to the api URL with JSON data to start scraping 
            start_scrape_url = 'http://127.0.0.1:5000/api/start'
            start_data = {'asin': asin_value}
            start_response = requests.put(start_scrape_url, json=start_data)

            if product_response.status_code == 200 and start_response.status_code == 200:
                result_icon_class = "fas fa-check-circle"
                result_message = "Successfully started scraping!"
            else:
                result_icon_class = "fas fa-times-circle"
                result_message = "Failed to start scraping"
                
        except Exception as e:
            result_icon_class = "fas fa-exclamation-triangle"  # Exclamation triangle icon for exceptions
            result_message = "Failed to connect to server"
            print("Exception:", str(e))  # Print the exception message for debugging

        return loading_icon_class, result_icon_class, result_message

    else:
        return "", "", ""



# callback to show the new product form
@app.callback(
    Output('form-modal', 'is_open', allow_duplicate=True),
    [Input('open-button', 'n_clicks'),
     Input('close-button', 'n_clicks')],
    [State('form-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_form_modal(open_clicks, close_clicks, is_open):
    if open_clicks or close_clicks:
        return not is_open
    return is_open



# callback to open prefilled with current product form
@app.callback(
    [Output('form-modal', 'is_open'),
     Output('input-asin', 'value', allow_duplicate=True),
     Output('input-product-name', 'value', allow_duplicate=True)],
    [Input('scrape-more-button', 'n_clicks'),
     Input('close-button', 'n_clicks')],
    [State('form-modal', 'is_open'),
     State('product-dropdown', 'value'),
     State("product-dropdown","options")],
    prevent_initial_call=True
)
def toggle_form_modal(scrape_more_clicks, close_clicks, is_open, current_asin, current_product_options):

    # parse out the label from the options based on the asin value
    selected_product_name = [x['label'] for x in current_product_options if x['value'] == current_asin]
    if len(selected_product_name) > 0:
        selected_product_name = selected_product_name[0]
    else:
        selected_product_name = None

    if scrape_more_clicks or close_clicks:
        return not is_open, current_asin, selected_product_name

    return is_open, current_asin, selected_product_name



# Callback to automatically uppercase ASIN
@app.callback(
    Output('input-asin', 'value'),
    [Input('input-asin', 'value')]
)
def update_asin_value(value):
    if value is not None:
        return value.upper()

    return ''

# Define the callback to display the selected product
@app.callback(
    [Output('selected-product', 'children'), 
     Output('figure-div', 'style'),
     Output('home-placeholder', 'style')],
    [Input('product-dropdown', 'value')],
    [State("product-dropdown","options")]
)
def display_selected_product(selected_product_asin, opt):

    fig_div_style = {'display': 'none'}
    placeholder_div_style = {'display': 'block', "padding": '20px'}

    # parse out the label from the options based on the asin value
    selected_product_name = [x['label'] for x in opt if x['value'] == selected_product_asin]
    if len(selected_product_name) > 0:
        selected_product_name = selected_product_name[0]
    else:
        selected_product_name = None

    product_info = []

    # format product name and asin
    if selected_product_name:
        product_info.append(html.H4([html.B("Selected Product:"), f' {selected_product_name}']))

        # if there is a selected product, hide place holder and show figures
        fig_div_style = {'display': 'block'}
        placeholder_div_style = {'display': 'none'}
    if selected_product_asin:
        product_info.append(html.H5([html.B("ASIN:"), f' {selected_product_asin}']))


    return html.Div(product_info), fig_div_style, placeholder_div_style



    

# callback to refresh products
@app.callback(
    Output('product-dropdown', 'options'),
    Input('refresh-button', 'n_clicks')
)
def update_dropdown_options(n_clicks):
    # Simulate fetching updated product data (product_names and asins)
    updated_product_names, updated_asins = get_products()
    
    options = [{'label': product_name, 'value': asin} for product_name, asin in zip(updated_product_names, updated_asins)]
    return options

# Define the callback to update the wordclouds
@app.callback(
    [Output('pos-wordcloud', 'children'),
     Output('neg-wordcloud', 'children')],
    [Input('product-dropdown', 'value')]
)
def update_wordclouds(asin):
    if asin:
        # Fetch the wordclouds for the selected ASIN
        image_urls = fetch_wordclouds(asin_to_fetch=asin)

        wordclouds = []


        # placeholders
        pos_wordcloud = html.Div()
        neg_wordcloud = html.Div()


        # check if positive world cloud exists
        if "pos_image_url" in image_urls:
            # check if image url is not none 
            # boto client returns none when cant find object in bucket
            if image_urls["pos_image_url"] is not None:
                # add positive wordcloud and label to return component
                pos_wordcloud = dbc.Col([
                                html.Div("Positive Review Wordcloud", className="main-subtitles"),
                                dcc.Loading(
                                    html.Img(src=image_urls["pos_image_url"])
                                    )]
                                )

        
        # check if negative world cloud exists
        if "neg_image_url" in image_urls:
            # check if image url is not none 
            # boto client returns none when cant find object in bucket
            if image_urls["neg_image_url"] is not None:
                # add negative wordcloud and label to return component
                neg_wordcloud = dbc.Col([
                                html.Div("Negative Review Wordcloud", className="main-subtitles",),
                                dcc.Loading(
                                    html.Img(src=image_urls["neg_image_url"])
                                    )]
                                )

        # Return the image components
        return pos_wordcloud, neg_wordcloud
    else:
        return html.Div(), html.Div()
    

# Define the callback to update the important words table
@app.callback(
    Output('important-words', 'children'),
    [Input('product-dropdown', 'value')]
)
def update_important_words(asin):
    if asin:
        # Fetch the wordclouds for the selected ASIN
        important_words_df = fetch_important_words_csv(asin=asin)
        
        # selecting top ten variables and removing id row
        important_words_df = important_words_df.iloc[:10, 1:3]

        if isinstance(important_words_df, pd.DataFrame):
            colored_words_table =  dbc.Col([

                html.Div("Important Words From Sentiment Model", className="main-subtitles",
                         style={'display': 'flex',
                                'justify-content': 'center'}),
                
                dash_table.DataTable(
                    data=important_words_df.to_dict('records'),
                            columns=[
                                {'id': 'feature', 'name': 'Word'},
                                {'id': 'coefficient', 'name': 'Coefficient', 'type': 'numeric'
                                 , "format": Format(precision=3, scheme=Scheme.fixed)}
                            ],
                            # conditional styling based on value of coefficient
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{coefficient} > 0'},
                                    'backgroundColor': '#90EE90',
                                    'color': '#013220'
                                },
                                {
                                    'if': { 'filter_query': '{coefficient} < 0'},
                                    'backgroundColor': '#ffcccb',
                                    'color': '#8B0000'
                                },
                            ],
                            style_cell={'textAlign': 'center'},
                            cell_selectable = False
                )
            ])

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
        html.Div('Number of Ratings by Month and Rating', className="main-subtitles",
                 style={'display': 'flex',
                        'justify-content': 'center',
                        'padding-bottom':'0ch'}),
        dcc.Graph(id='rating-counts-plot', figure=fig)
    ])

    review_count_display = html.Div([html.Div("Reviews Scraped", style={'display': 'flex',
                                                                        'justify-content': 'center'},
                                               className="main-subtitles"),
                                     CircularComponent(len(reviews_df))]) 
    return graph, review_count_display




# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)

