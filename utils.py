import extruct
from objects import Article, Person
import wikipedia
from bs4 import BeautifulSoup

# read config file
import yaml

with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


def extract_metadata(text):
    """
    Extract all metadata present in the page and return a dictionary of metadata lists.

        Initially authored by Ricardo Usbeck

    Args:

    Returns:
        metadata (dict): Dictionary of json-ld, microdata, and opengraph lists.
        Each of the lists present within the dictionary contains multiple dictionaries.
    """

    metadata = extruct.extract(text,
                               uniform=True,
                               syntaxes=['json-ld',
                                         'microdata',
                                         'opengraph'])
    return metadata


def is_author_in(name, authors):
    """
    Verifies if the author is already in the results
    Args:
        name: name of the author
        authors: list of the results

    Returns:
        True if it's already there and False if not

    """
    for author in authors:
        if type(author) is not Person:
            continue
        if author.name == name:
            return author
    return None


def is_article_in(title, articles):
    """
        Verifies if the paper is already in the results
        Args:
            title: name of the paper
            articles: list of the results

        Returns:
            True if it's already there and False if not

        """
    for article in articles:
        if type(article) is not Article:
            continue
        if article.title == title:
            return article
    return None


def read_wikipedia(title):
    wikipedia.set_lang("en")
    try:
        summary_text = wikipedia.summary(title, 3, redirect=True)
    except:
        return ""
    return summary_text


# def remove_html_tags(text):
#     soup = BeautifulSoup(text, "html.parser")
#     cleaned_text = soup.text
#     cleaned_text.strip()
#     sentences = cleaned_text.split('.')
#     if len(sentences) <= 5:
#         return cleaned_text
#     else:
#         first_n_sentences: str = '. '.join(
#                 sentence for sentence in sentences[0:4])
#         return first_n_sentences


def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.text.strip()


def remove_line_tags(text):
    return text.replace('\n', ' ').replace('\t', ' ')


# region DECORATORS

from functools import wraps
from time import time
import inspect
import os


def timeit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ts = time()
        result = f(*args, **kwargs)
        te = time()
        filename = os.path.basename(inspect.getfile(f))
        print('file:%r func:%r took: %2.4f sec' % (filename, f.__name__, te - ts))
        return result

    return decorated_function

# endregion
