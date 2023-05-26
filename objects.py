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
    name: str
    url: str
    h_index: int


@dataclasses.dataclass
class Funder:
    name: str
    description: str
    grants_count: int
    homepage_url: str
