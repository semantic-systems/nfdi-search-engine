import dataclasses
from typing import Union

@dataclasses.dataclass
class thing:
    name: str
    alternateName: str
    description: str
    url: str
    image: str #url of the image

@dataclasses.dataclass
class Organization(thing):
    address: str
    email: str
    legalName: str
    location: str
    logo: str # url
    numberOfEmployees: str
    telephone: str

@dataclasses.dataclass
class Person(thing):
    additionalName: str
    address: str
    affiliation: Organization
    alumniOf: Organization
    birthDate: str
    birthPlace: str
    deathDate: str
    deathPlace: str
    email: str
    familyName: str
    gender: str
    givenName: str # usually the first name
    homeLocation: str
    honorificPrefix: str #An honorific prefix preceding a Person's name such as Dr/Mrs/Mr.
    honorificSuffix: str #An honorific suffix following a Person's name such as M.D./PhD/MSCSW.
    jobTitle: str
    nationality: str # we can later link it to country 
    workLocation: str
    worksFor: Organization

@dataclasses.dataclass
class CreativeWork(thing):
    abstract: str
    accountablePerson: Person
    alternativeHeadline: str
    author: Person
    citation: str # this should actually reference to articles
    countryOfOrigin: str
    creativeWorkStatus: str
    dateCreated: str
    dateModified: str
    datePublished: str
    funder: Union[Organization, Person]  # Organization | Person # we can use pipe operator for Union in Python >= 3.10 
    funding: str # we can change this to Grant
    genre: str
    headline: str
    inLanguage: str
    keywords: str
    license: str # url or license type
    publication: str #publication event
    publisher: Union[Organization, Person]
    sourceOrganization: Organization
    sponsor: Union[Organization, Person]
    text: str
    thumbnail: str #ImageObject
    thumbnailUrl: str #url
    version: str   


@dataclasses.dataclass
class Article:
    title: str
    url: str
    authors: str
    description: str
    date: str
    articleBody: str
    pageEnd: str
    pageStart: str
    pagination: str
    wordCount: str


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


@dataclasses.dataclass
class Orcid:
    id: str
    url: str
    name: str


@dataclasses.dataclass
class Gepris:
    url: str
    title: str
    description: str
    date: str
    applicant_or_leader:str
