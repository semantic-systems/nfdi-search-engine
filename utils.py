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
            return True
    return False


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
            return True
    return False
