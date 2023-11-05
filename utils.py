import extruct
from objects import Article, Person
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
    # print("---"*30)
    # print(text)
    soup = BeautifulSoup(text, "html.parser")
    return soup.text.strip()

def get_first_item_from_list(list):
    return next(iter(list), None)

def get_majority_vote_from_dict(dict):
    sorted_dict = sorted(dict, key=dict.get, reverse=True)
    return next(iter(sorted_dict), None)


import csv
def convert_publications_to_csv(publications):
    with open('entity-resolution/training-data-publications.csv', 'w', newline='', encoding="utf-8") as csv_file:
        wr = csv.writer(csv_file, delimiter=',')
        wr.writerow(["Title", "Authors", "Abstract", "Source", "DatePublished"])
        for publication in publications:            
            wr.writerow(list([publication.name, 
                             "; ".join([author.name for author in publication.author]),                             
                             publication.description,
                             publication.source,
                             publication.datePublished]
                             ))  

from collections import defaultdict
import dedupe
@timeit
def perform_entity_resolution_publications(publications):

    data_publications = {}
    for idx, publication in enumerate(publications):
        row_publication = {
            'Title': None,
            'Authors': None,
            'Abstract': None,
            'Source': None,
            'DatePublished': None
        }
        if publication.name != '':
            row_publication['Title'] = publication.name
        publication_authors = "; ".join([author.name for author in publication.author])
        if publication_authors != '':
            row_publication['Authors'] = publication_authors
        if publication.description != '':
            row_publication['Abstract'] = publication.description
        if publication.source != '':
            row_publication['Source'] = publication.source
        if publication.datePublished != '':
            row_publication['DatePublished'] = publication.datePublished

        data_publications[idx] = row_publication

    settings_file = config['settings_file_publications']
    if os.path.exists(settings_file):
        print('reading from', settings_file)
        with open(settings_file, 'rb') as sf:
            deduper = dedupe.StaticDedupe(sf, num_cores=2)
    else:
        print('Setting file not found: ', settings_file)

    clustered_dupes = deduper.partition(data_publications, 0.5)
    indices_to_drop = []
    for cluster_id, (records, scores) in enumerate(clustered_dupes):
        if len(records) > 1:
            # merge all the instances in this cluster into one

            # sources, names, authors, descriptions, published_dates, inlanguages, licenses  = (defaultdict(int) for i in range(7)) 
            sources, names, authors, descriptions, published_dates = (defaultdict(int) for i in range(5)) 
            for record_id in records:
                sources[str(publications[record_id].source)] += 1
                if publications[record_id].name != "":
                    names[publications[record_id].name] += 1
                if len(publications[record_id].author) > 0:
                    authors[str(publications[record_id].author)] += 1
                if publications[record_id].description != "":
                    descriptions[publications[record_id].description] += 1
                if publications[record_id].datePublished != "":
                    published_dates[publications[record_id].datePublished] += 1
                # if len(publications[record_id].inLanguage) > 0:
                #     inlanguages[str(publications[record_id].inLanguage)] += 1
                # if publications[record_id].license != "":
                #     licenses[publications[record_id].license] += 1
                indices_to_drop.append(record_id)

            publication = Article()  
            for src in sources.keys():
                publication.source.append(src)
            publication.name = "MERGED - " + get_majority_vote_from_dict(names)
            publication.author = get_majority_vote_from_dict(authors)
            publication.description = get_majority_vote_from_dict(descriptions)
            publication.datePublished = get_majority_vote_from_dict(published_dates)
            
            # publication.name = "MERGED - " + get_first_item_from_list(sorted(names, key=names.get, reverse=True))
            # publication.author = get_first_item_from_list(sorted(authors, key=authors.get, reverse=True))
            # publication.description = get_first_item_from_list(sorted(descriptions, key=descriptions.get, reverse=True))
            # publication.datePublished = get_first_item_from_list(sorted(published_dates, key=published_dates.get, reverse=True))
            # publication.inLanguage = get_first_item_from_list(sorted(inlanguages, key=inlanguages.get, reverse=True))
            # publication.license = get_first_item_from_list(sorted(licenses, key=licenses.get, reverse=True))

            publications.append(publication)

            # publication = Article()            
            # for record_id in records:
            #     publication.source.append(publications[record_id].source)
            #     if publication.name is None or publication.name == "":
            #         publication.name = publications[record_id].name
            #     if publication.author is None or len(publication.author) == 0:
            #         publication.author = publications[record_id].author
            #     if publication.description is None or publication.description == "":
            #         publication.description = publications[record_id].description
            #     if publication.datePublished is None or publication.datePublished == "":
            #         publication.datePublished = publications[record_id].datePublished
            #     if publication.inLanguage is None or len(publication.inLanguage) == 0:
            #         publication.inLanguage = publications[record_id].inLanguage
            #     if publication.license is None or publication.license == "":
            #         publication.license = publications[record_id].license
            #     indices_to_drop.append(record_id)
            # publications.append(publication)
    
    # for index in sorted(indices_to_drop, reverse=True):
    #     del publications[index]
    
    return publications


