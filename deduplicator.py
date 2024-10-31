import csv
import utils
from collections import defaultdict
import dedupe
import os
from objects import thing, Article, Author
import pickle

def get_first_item_from_list(list):
    return next(iter(list), '')

def get_majority_vote_from_dict(dict):
    sorted_dict = sorted(dict, key=dict.get, reverse=True)
    return next(iter(sorted_dict), '')

def convert_publications_to_csv(publications):
    with open('entity-resolution/training-data-publications.csv', 'w', newline='', encoding="utf-8") as csv_file:
        wr = csv.writer(csv_file, delimiter=',')
        wr.writerow(["identifier","name", "url", "author", "description", "datePublished", "source_name", "source_identifier", "source_url"])
        for publication in publications:            
            wr.writerow(list([publication.identifier,
                             publication.name, 
                             publication.url,
                             "; ".join([author.name for author in publication.author]),                             
                             publication.description,
                             publication.datePublished,
                             publication.source[0].name,
                             publication.source[0].identifier,
                             publication.source[0].url
                             ]
                             ))  


    
@utils.timeit
def perform_entity_resolution_publications(app, publications):

    data_publications = {}
    for idx, publication in enumerate(publications):
        row_publication = {
            'identifier': None,
            'name': None,
            'url': None,
            'author': None,
            'description': None,
            'datePublished': None,
            'source_name': None,
            'source_identifier': None,
            'source_url': None
        }

        if publication.identifier != '':
            row_publication['identifier'] = str(publication.identifier)
        if publication.name != '':
            row_publication['name'] = str(publication.name)
        if publication.url != '':
            row_publication['url'] = str(publication.url)        
        publication_authors = "; ".join([author.name for author in publication.author])
        if publication_authors != '':
            row_publication['author'] = publication_authors
        if publication.description != '':
            row_publication['description'] = str(publication.description)
        if publication.datePublished != '':
            row_publication['datePublished'] = str(publication.datePublished)
        if publication.source[0].name != '':
            row_publication['source_name'] = str(publication.source[0].name)
        if publication.source[0].identifier != '':
            row_publication['source_identifier'] = str(publication.source[0].identifier)
        if publication.source[0].url != '':
            row_publication['source_url'] = str(publication.source[0].url)     

        data_publications[idx] = row_publication

    settings_file = app.config["ENTITY_RESOLUTION"]['settings_file_publications']
    if os.path.exists(settings_file):
        print('reading from', settings_file)
        with open(settings_file, 'rb') as sf:
            deduper = dedupe.StaticDedupe(sf, num_cores=1)
    else:
        print('Setting file not found: ', settings_file)

    clustered_dupes = deduper.partition(data_publications, 0.5)
    indices_to_drop = []
    for cluster_id, (records, scores) in enumerate(clustered_dupes):
        if len(records) > 1:
            # merge all the instances in this cluster into one

            # sources, names, authors, descriptions, published_dates, inlanguages, licenses  = (defaultdict(int) for i in range(7)) 
            # identifiers, names, urls, authors, descriptions, published_dates, source_names, source_identifiers, source_urls = (defaultdict(int) for i in range(9)) 
            identifiers, names, urls, authors, descriptions, published_dates = (defaultdict(int) for i in range(6)) 
            sources = []
            for record_id in records:
                if publications[record_id].identifier != "":
                    identifiers[publications[record_id].identifier] += 1
                if publications[record_id].name != "":
                    names[publications[record_id].name] += 1
                if publications[record_id].url != "":
                    urls[publications[record_id].url] += 1
                if len(publications[record_id].author) > 0:
                    authors[pickle.dumps(publications[record_id].author)] += 1
                if publications[record_id].description != "":
                    descriptions[publications[record_id].description] += 1
                if publications[record_id].datePublished != "":
                    published_dates[publications[record_id].datePublished] += 1
                
                sources.append(publications[record_id].source[0])
                
                # if len(publications[record_id].inLanguage) > 0:
                #     inlanguages[str(publications[record_id].inLanguage)] += 1
                # if publications[record_id].license != "":
                #     licenses[publications[record_id].license] += 1

                indices_to_drop.append(record_id)

            publication = Article()    

            # load the merged/combined record on the basis of majority voting          
            publication.identifier = get_majority_vote_from_dict(identifiers)
            publication.name = "MERGED - " + get_majority_vote_from_dict(names)
            publication.url = get_majority_vote_from_dict(urls)            
            publication.description = get_majority_vote_from_dict(descriptions)
            publication.datePublished = get_majority_vote_from_dict(published_dates)

            #get majority vote method will return the string which should be converted to list of authors
            authors_majority_vote = get_majority_vote_from_dict(authors)           
            publication.author.extend(pickle.loads(authors_majority_vote))
            
            for src in sources:
                publication.source.append(src)

            publications.append(publication)
            
            # load the merged/combined record on the basis of first non-null record/attribute    
            # publication.name = "MERGED - " + get_first_item_from_list(sorted(names, key=names.get, reverse=True))
            # publication.author = get_first_item_from_list(sorted(authors, key=authors.get, reverse=True))
            # publication.description = get_first_item_from_list(sorted(descriptions, key=descriptions.get, reverse=True))
            # publication.datePublished = get_first_item_from_list(sorted(published_dates, key=published_dates.get, reverse=True))
            # publication.inLanguage = get_first_item_from_list(sorted(inlanguages, key=inlanguages.get, reverse=True))
            # publication.license = get_first_item_from_list(sorted(licenses, key=licenses.get, reverse=True))
            # for src in sources:
            #     publication.source.append(src)
            # publications.append(publication)

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


