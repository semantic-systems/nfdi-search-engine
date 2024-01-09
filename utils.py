import extruct
from objects import Article, Person, Author
import wikipedia
from bs4 import BeautifulSoup

# read config file
import yaml
with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)



#region DECORATORS

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
        print('file:%r func:%r took: %2.4f sec' % (filename, f.__name__, te-ts))
        return result
    return decorated_function

#endregion


def clean_json(value):
    """
    Recursively remove all None values from dictionaries and lists, and returns
    the result as a new dictionary or list.
    """
    if isinstance(value, list):
        return [clean_json(x) for x in value if x is not None]
    elif isinstance(value, dict):
        return {
            key: clean_json(val)
            for key, val in value.items()
            if val is not None
        }
    else:
        return value

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

def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.text.strip()

def remove_line_tags(text):
    return text.replace('\n', ' ').replace('\t', ' ')


from dateparser import parse
def parse_date(date_str):
    try:
        parsed_date_str = parse(date_str).strftime("%Y-%m-%d")
        return parsed_date_str
    except (TypeError, ValueError):
        print(f"original date str: {date_str}")
        return ""
        
def sort_results_publications(results):
    def custom_sort_key(obj):    
        desc = getattr(obj, 'description', '') 
        pub_date = getattr(obj, 'datePublished', '0000-00-00') 
        if desc == '':
            return (0, pub_date)
        return (1, pub_date)

    return sorted(results, key=custom_sort_key, reverse=True)

def split_authors(authors_names, seperator, authors_list):
    authors = authors_names.split(seperator)
    for author in authors:
        _author = Author()
        _author.type = 'Person'
        _author.name = author
        authors_list.append(_author)  

    