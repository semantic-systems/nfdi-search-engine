import requests
import utils
# from objects import Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Person, LearningResource, CreativeWork, VideoObject, ImageObject
from objects import thing, Article, Statistics, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
import logging
from sources import data_retriever
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term, results):

    source = "Zenodo"
    try:
        search_result = data_retriever.retrieve_data(source=source,
                                                     base_url=utils.config["search_url_zenodo"],
                                                     search_term=search_term,
                                                     results=results)

        total_records_found = search_result.get("hits", {}).get("total", 0)
        hits = search_result.get("hits", {}).get("hits", [])
        total_hits = len(hits)
        logger.info(f'{source} - {total_records_found} records matched; pulled top {total_hits}')

        if int(total_hits) > 0:
            for hit in hits:

                metadata = hit.get('metadata', {})
                resource_type = metadata.get('resource_type', {}).get('type','OTHER').upper()

                if resource_type == 'PUBLICATION':
                    digitalObj = Article()
                elif resource_type in ['PRESENTATION', 'POSTER']:
                    digitalObj = CreativeWork()
                elif resource_type == 'DATASET':
                    digitalObj = Dataset()
                elif resource_type == 'VIDEO':
                    digitalObj = VideoObject()
                elif resource_type == 'IMAGE':
                    digitalObj = ImageObject()
                elif resource_type == 'LESSON':
                    digitalObj = LearningResource()
                elif resource_type == 'SOFTWARE':
                    digitalObj = SoftwareApplication()
                elif resource_type == 'OTHER':
                    digitalObj = CreativeWork()
                else:
                    print('This resource type is still not defined:', resource_type)
                    digitalObj = CreativeWork()

                digitalObj.identifier = hit.get('doi', '')
                digitalObj.name = hit.get('title', '')
                digitalObj.url = hit.get('links', {}).get('self', '')
                digitalObj.genre = resource_type
                digitalObj.description = utils.remove_html_tags(metadata.get('description', ''))

                keywords = metadata.get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        terms = [term.strip() for term in keyword.split(",")]
                        digitalObj.keywords.extend(terms)

                language = metadata.get('language', '')
                digitalObj.inLanguage.append(language)
                digitalObj.dateCreated = hit.get('created','')
                digitalObj.dateModified = hit.get('modified','')
                digitalObj.datePublished = metadata.get('resource_date', '')
                digitalObj.license = metadata.get('license', {}).get('id', '')
                digitalObj.creativeWorkStatus = hit.get('status','')
                digitalObj.funder = metadata.get('grants', [{}])[0].get('funder', {}).get('name', '')
                digitalObj.conditionsOfAccess = metadata.get('access-rights','')
                if(digitalObj.conditionsOfAccess == ''):
                    digitalObj.conditionsOfAccess = metadata.get('access_right','')

                relation_map = {
                    'iscitedby': 'isCitedBy',
                    'issupplementto': 'isSupplementTo',
                    'ispartof': 'isPartOf',
                    'cites': 'cites',
                    'issourceof': 'isSourceOf',
                    'isderivedfrom': 'isDerivedFrom',
                    'issupplementedby': 'isSupplementedBy',
                    'ispreviousversionof': 'isPreviousVersionOf',
                    'documents': 'documents',
                    'haspart': 'hasPart'
                }

                related_identifiers = metadata.get('related_identifiers', [])

                for related_identifier in related_identifiers:
                    relation = related_identifier.get('relation', '').lower()
                    identifier = related_identifier.get('identifier', '')

                    if relation == 'iscitedby':
                        digitalObj.isCitedBy.append(identifier)
                    elif relation == 'issupplementto':
                        digitalObj.isSupplementTo.append(identifier)
                    elif relation == 'ispartof':
                        digitalObj.isPartOf.append(identifier)
                    elif relation == 'cites':
                        digitalObj.cites.append(identifier)
                    elif relation == 'issourceof':
                        digitalObj.isSourceOf.append(identifier)
                    elif relation == 'isderivedfrom':
                        digitalObj.isDerivedFrom.append(identifier)
                    elif relation == 'issupplementedby':
                        digitalObj.isSupplementedBy.append(identifier)
                    elif relation == 'ispreviousversionof':
                        digitalObj.isPreviousVersionOf.append(identifier)
                    elif relation == 'documents':
                        digitalObj.documents.append(identifier)
                    elif relation == 'haspart':
                        digitalObj.hasPart.append(identifier)

                authors = metadata.get("creators", [])
                for author in authors:
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = author.get("name", "")
                    _author.identifier = author.get("orcid", "")
                    _author.affiliation = author.get("affiliation", "")
                    digitalObj.author.append(_author)

                Stats = hit.get('stats', '')
                _stats = Statistics()

                _stats.downloads = Stats.get("downloads", '')
                _stats.unique_downloads = Stats.get("unique_downloads", '')
                _stats.views = Stats.get("views", '')
                _stats.unique_views = Stats.get("unique_views", '')
                _stats.version_downloads = Stats.get("version_downloads", '')
                _stats.version_unique_downloads = Stats.get("version_unique_downloads", '')
                _stats.version_unique_views = Stats.get("version_unique_views", '')
                _stats.version_views = Stats.get("version_views", '')

                digitalObj.stats = _stats

                contributors = metadata.get("contributors", [])
                for contributor in contributors:
                    _contributor = Author()
                    _contributor.type = 'Person'
                    _contributor.name = contributor.get("name", "")
                    _contributor.identifier = contributor.get("orcid", "")
                    _contributor.affiliation = contributor.get("affiliation", "")
                    digitalObj.contributor.append(_contributor)

                _source = thing()
                _source.name = source
                _source.identifier = hit.get("id", "")
                _source.url = hit.get('links', {}).get('self_html', '')
                digitalObj.source.append(_source)

                files = hit.get('files', [])

                # if resource_type == "LESSON":
                for file in files:
                    file_key = file.get("key", "")
                    digitalObj.encoding_contentUrl[file_key] = file.get("links", {}).get("self", "")

                digitalObj.softwareVersion = metadata.get("version", "")
                if resource_type.upper() == 'PUBLICATION':
                    digitalObj.abstract = digitalObj.description
                    pages = hit.get("journal", {}).get('pages', '')
                    if '-' in pages:
                        a, b = pages.split('-')
                        digitalObj.pageStart = a.strip()
                        digitalObj.pageEnd = b.strip()
                    else:
                        digitalObj.pageStart = pages
                        digitalObj.pageEnd = ''

                    digitalObj.pagination = pages

                    journal_info = metadata.get('journal', {})
                    digitalObj.Journal = journal_info.get('title', '')
                    digitalObj.JournalVolume = journal_info.get('volume', '')
                    digitalObj.issue = journal_info.get('issue', '')

                    results['publication'].append(digitalObj)
                elif resource_type.upper() in ['PRESENTATION', 'POSTER', 'DATASET', 'SOFTWARE', 'VIDEO', 'IMAGE', 'LESSON']:
                    results['resources'].append(digitalObj)
                else:
                    results['others'].append(digitalObj)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())


@utils.timeit
def get_resource(doi: str):

    source = "Zenodo"
    start_index = doi.find("zenodo.") + len("zenodo.")
    if start_index!= -1:
        doi = doi[start_index:]
    else:
        doi = doi

    try:
        search_results = data_retriever.retrieve_single_object(source=source,
                                                     base_url=utils.config["search_url_zenodo"],
                                                     doi = doi)
        search_result = search_results.get("hits", {}).get("hits", [])
        search_result = search_result[0]
        metadata = search_result.get('metadata', {})
        resource = CreativeWork()
        resource.name = search_result.get("title", "")
        resource.url = search_result.get('links', {}).get('self', '')
        resource.identifier = search_result.get("doi", "")
        resource.datePublished = metadata.get("publication_date", "")
        resource.inLanguage.append(metadata.get("language", ""))
        resource.license = metadata.get("license", "")
        files = search_result.get('files','')
        resource.encoding_contentUrl = {file["key"]: file["links"]["self"] for file in files}
        resource.description =  utils.remove_html_tags(metadata.get("description", ""))
        resource.abstract = resource.description
        authors = metadata.get("creators", [])
        for author in authors:
            _author = Author()
            _author.type = 'Person'
            _author.name = author.get("name", "")
            _author.identifier = author.get("orcid", "")
            _author.affiliation = author.get("affiliation", "")
            resource.author.append(_author)

        keywords = metadata.get('keywords', [])
        if isinstance(keywords, list):
            for keyword in keywords:
                terms = [term.strip() for term in keyword.split(",")]
                resource.keywords.extend(terms)

        return resource

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())