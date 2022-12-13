import extruct
from objects import Article, Person

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
    for author in authors:
        if type(author) is not Person:
            print(type(author))
            continue
        if author.name == name:
            return True
    return False


def is_article_in(title, articles):
    for article in articles:
        if type(article) is not Article:
            continue
        if article.title == title:
            return True
    return False
