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
    date: str


@dataclasses.dataclass
class Zenodo:
    resource_type: str
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
    author: str


@dataclasses.dataclass
class Institute:
    name: str
    url: str
    country: str


@dataclasses.dataclass
class Presentation:
    title: str
    url: str
    authors: str
    date: str


@dataclasses.dataclass
class Poster:
    title: str
    url: str
    authors: str
    date: str


@dataclasses.dataclass
class Dataset:
    title: str
    url: str
    authors: str
    version_unique_downloads: int
    version_unique_views: int


@dataclasses.dataclass
class Software:
    title: str
    url: str
    version: str
    version_unique_downloads: int
    version_unique_views: int


@dataclasses.dataclass
class Image:
    title: str
    owner: str
    url: str


@dataclasses.dataclass
class Video:
    title: str
    url: str
    creators: str


@dataclasses.dataclass
class Lesson:
    title: str
    url: str
    authors: str
    
    
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
