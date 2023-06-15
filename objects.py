import dataclasses


@dataclasses.dataclass
class Person:
    name: str
    url: str
    affiliation: str


@dataclasses.dataclass
class Article:
    title: str
    url: str
    authors: str
    description: str
    date: str


@dataclasses.dataclass
class Zenodo:
    resource_type: str
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
    description: str
    author: str


@dataclasses.dataclass
class Institute:
    name: str
    id: str
    country: str
    institute_type: str
    acronyms_name: str
    homepage_url: str
    description: str



@dataclasses.dataclass
class Presentation:
    title: str
    url: str
    authors: str
    description: str
    date: str


@dataclasses.dataclass
class Poster:
    title: str
    url: str
    authors: str
    description: str
    date: str


@dataclasses.dataclass
class Dataset:
    title: str
    url: str
    authors: str
    description: str
    date: str


@dataclasses.dataclass
class Software:
    title: str
    url: str
    date: str
    authors: str
    description: str
    version: str


@dataclasses.dataclass
class Image:
    title: str
    authors: str
    url: str
    date: str


@dataclasses.dataclass
class Video:
    title: str
    url: str
    authors: str
    date: str


@dataclasses.dataclass
class Lesson:
    title: str
    url: str
    authors: str
    description: str
    date: str

    
@dataclasses.dataclass
class Publisher:
    id: str
    name: str
    homepage_url: str
    country_codes: str
    works_count: str
    h_index: str
    description: str


@dataclasses.dataclass
class Funder:
    name: str
    id: str
    description: str
    country_code: str
    grants_count: str
    homepage_url: str
    works_count: str


@dataclasses.dataclass
class Gesis:
    resource_type: str
    url: str
    date: str 
    title: str
    description: str
    authors: str


@dataclasses.dataclass
class Cordis:
    id: str
    url: str
    date: str 
    title: str
    description: str