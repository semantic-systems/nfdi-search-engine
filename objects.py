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
class Ieee:
    title: str
    url: str
    date: str
    authors: str
        
        
@dataclasses.dataclass
class Institute:
    name: str
    url: str
    country: str
