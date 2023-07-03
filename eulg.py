from objects import Dataset, Software
import utils
from elg import Catalog


def search(search_term, results):
    catalog = Catalog()
    resource_items = ["Corpus", "Tool/Service", "Lexical/Conceptual resource"]  # "Language description"]
    for resource_item in resource_items:
        elg_results = catalog.search(
            resource=resource_item,     # languages = ["English","German"], # string or list if multiple languages
            search=search_term,
            limit=100,
        )
        for result in elg_results:
            description = result.description
            description = utils.remove_html_tags(description)
            if result.resource_type == 'Corpus' or result.resource_type == 'Lexical/Conceptual resource':
                if result.resource_type == 'Corpus':
                    url = 'https://live.european-language-grid.eu/catalogue/corpus/' + str(result.id)
                if result.resource_type == 'Lexical/Conceptual resource':
                    url = 'https://live.european-language-grid.eu/catalogue/lcr/' + str(result.id)
                results.append(
                    Dataset(
                        title=result.resource_name,
                        authors=result.resource_type,
                        url=url,
                        description=description,
                        date=result.creation_date
                    )
                )
            elif result.resource_type == "Tool/Service":
                url = "https://live.european-language-grid.eu/catalogue/tool-service/" + str(result.id)
                description = result.description
                description = utils.remove_html_tags(description)
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
                # languages=', '.join(str(language) for language in result.languages)
