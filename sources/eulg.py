from objects import Dataset, Software
import utils
from elg import Catalog

@utils.timeit
def search(search_term, results):
    catalog = Catalog()
    resource_items = ["Corpus", "Tool/Service", "Lexical/Conceptual resource"]  # "Language description"]
    for resource_item in resource_items:
        elg_results = catalog.search(
            resource=resource_item,  # languages = ["English","German"], # string or list if multiple languages
            search=search_term,
            limit=100,
        )
        for result in elg_results:
            description = result.description

            first_license: str = ''
            if result.licences:
                first_license = result.licences[0]

            description = utils.remove_html_tags(description)
            if result.resource_type == 'Corpus' or result.resource_type == 'Lexical/Conceptual resource':
                url = ''
                if result.resource_type == 'Corpus':
                    url = 'https://live.european-language-grid.eu/catalogue/corpus/' + str(result.id)
                if result.resource_type == 'Lexical/Conceptual resource':
                    url = 'https://live.european-language-grid.eu/catalogue/lcr/' + str(result.id)

                dataset = Dataset()
                dataset.source = 'elg:corpus'
                dataset.name = result.resource_name
                dataset.url = url
                dataset.datePublished = str(result.creation_date)
                dataset.description = description
                keywords = result.keywords
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            dataset.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            dataset.keywords.append(items['key'])
                else:
                    dataset.keywords.append('')

                languages = result.languages
                if isinstance(languages, list):
                    for language in languages:
                        for key in language.split(","):
                            dataset.inLanguage.append(key)
                elif isinstance(languages, dict):
                    for language in languages.get('buckets', []):
                        for items in language:
                            dataset.inLanguage.append(items['key'])
                else:
                    dataset.inLanguage.append('')

                # dataset.license = ', '.join(str(licence) for licence in result.licences)
                dataset.license = first_license
                dataset.countryOfOrigin = result.country_of_registration
                results['resources'].append(dataset)
                '''
                results.append(
                    Dataset(
                        title=result.resource_name,
                        authors=result.resource_type,
                        url=url,
                        description=description,
                        date=result.creation_date
                    )
                )
                '''
            elif result.resource_type == "Tool/Service":
                software = Software()
                url = "https://live.european-language-grid.eu/catalogue/tool-service/" + str(result.id)
                description = result.description
                description = utils.remove_html_tags(description)
                software.source = 'elg:software/service'
                software.name = result.resource_name
                software.url = url
                software.description = description
                software.datePublished = str(result.creation_date)
                software.countryOfOrigin = result.country_of_registration
                keywords = result.keywords
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            software.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            software.keywords.append(items['key'])
                else:
                    software.keywords.append('')

                languages = result.languages
                if isinstance(languages, list):
                    for language in languages:
                        for key in language.split(","):
                            software.inLanguage.append(key)
                elif isinstance(languages, dict):
                    for language in languages.get('buckets', []):
                        for items in language:
                            software.inLanguage.append(items['key'])
                else:
                    software.inLanguage.append('')

                # software.license = ', '.join(str(licence) for licence in result.licences)
                software.license = first_license
                results['resources'].append(software)
                '''
                results.append(
                    Software(
                        url=url,
                        title=result.resource_name,
                        authors=result.resource_type,
                        date=result.creation_date,
                        description=description,
                        version=', '.join(str(licence) for licence in result.licences)
                    )
                )
                '''
                # languages=', '.join(str(language) for language in result.languages)
