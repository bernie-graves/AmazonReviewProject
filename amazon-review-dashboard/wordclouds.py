
from collections import Counter
import wordcloud
import pandas as pd
import matplotlib.pyplot as plt
from os import path
from PIL import Image
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator



plt.rcParams["figure.figsize"] = [16, 9]


def create_ngrams(token_list, nb_elements):
    """
    Create n-grams for list of tokens
    Parameters
    ----------
    token_list : list
        list of strings
    nb_elements :
        number of elements in the n-gram
    Returns
    -------
    Generator
        generator of all n-grams
    """
    ngrams = zip(*[token_list[index_token:] for index_token in range(nb_elements)])
    return (" ".join(ngram) for ngram in ngrams)


def frequent_words(list_words, ngrams_number=1, number_top_words=10):
    """
    Create n-grams for list of tokens
    Parameters
    ----------
    ngrams_number : int
    number_top_words : int
        output dataframe length
    Returns
    -------
    DataFrame
        Dataframe with the entities and their frequencies.
    """
    frequent = []
    if ngrams_number == 1:
        pass
    elif ngrams_number >= 2:
        list_words = create_ngrams(list_words, ngrams_number)
    else:
        raise ValueError("number of n-grams should be >= 1")
    counter = Counter(list_words)
    frequent = counter.most_common(number_top_words)
    return frequent


def make_word_cloud(text_or_counter, stop_words=None):
    if isinstance(text_or_counter, str):
        word_cloud = wordcloud.WordCloud(stopwords=stop_words).generate(text_or_counter)
    else:
        if stop_words is not None:
            text_or_counter = Counter(word for word in text_or_counter if word not in stop_words)
        word_cloud = wordcloud.WordCloud(stopwords=stop_words).generate_from_frequencies(text_or_counter)
    plt.imshow(word_cloud)
    plt.axis("off")
    plt.show()


if __name__ == "__main__":
    df = pd.read_json("reviews_both.json")

    magnetic_charger = df[df["asin"] == "B0BPR6FL7M"]
    ab_charger = df[df["asin"] == "B01GGKYKQM"]

    
    
    # # Create stopword list:
    # stopwords = set(STOPWORDS)
    # stopwords.update(["charge", "charging", "cable"])
    # # Start with one review:

    # positive_reviews = ab_charger[ab_charger["rating"] >3]

    # positive_reviews_text = " ".join(review for review in positive_reviews["text"])


    # # Create and generate a word cloud image:
    # pos_wordcloud = WordCloud(stopwords=stopwords, background_color="white", width=1600, height=800).generate(positive_reviews_text)

    # # Display the generated image:
    # plt.imshow(pos_wordcloud, interpolation='bilinear')
    # plt.axis("off")
    # plt.show()

    # neg_reviews = ab_charger[ab_charger["rating"] < 3]

    # neg_reviews_text = " ".join(review for review in neg_reviews["text"])


    # # Create and generate a word cloud image:
    # neg_wordcloud = WordCloud(stopwords=stopwords, background_color="white", width=1600, height=800, colormap="magma").generate(neg_reviews_text)

    # # Display the generated image:
    # plt.imshow(neg_wordcloud, interpolation='bilinear')
    # plt.axis("off")
    # plt.show()




    
