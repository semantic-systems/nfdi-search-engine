import dataclasses

from rdflib import URIRef


@dataclasses.dataclass
class Person:
    name: str
    url: str


@dataclasses.dataclass
class Article:
    title: str
    url: str
    authors: str
    date: str


@dataclasses.dataclass
class Zenodo:
    uri: URIRef
    resource_type: URIRef
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
