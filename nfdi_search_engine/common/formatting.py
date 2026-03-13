from bs4 import BeautifulSoup


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


def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.text.strip()


def remove_line_tags(text):
    return text.replace('\n', ' ').replace('\t', ' ')
