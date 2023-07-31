from typing import Union, List
import dataclasses
from dataclasses import dataclass, fields, field

@dataclass
class thing:
    name: str = ""
    alternateName: str = ""
    description: str = ""
    url: str = ""
    image: str = "" #url of the image
    identifier: str = ""
    source: str = ""

    def __post_init__(self):
    # Loop through the fields
        for field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)

@dataclass
class Organization(thing):
    address: str = ""
    email: str = ""
    legalName: str = ""
    location: str = ""
    logo: str = "" # url
    numberOfEmployees: str = ""
    telephone: str = ""
    foundingDate: str = ""
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self):
    # Loop through the fields
        for field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)

@dataclass
class Person(thing):
    additionalName: str = ""
    address: str = "" #this should be a list
    affiliation: Organization = None  #this should be a list
    alumniOf: Organization = None  #this should be a list
    birthDate: str = ""
    birthPlace: str = ""
    deathDate: str = ""
    deathPlace: str = ""
    email: str = ""  #this should be a list
    familyName: str = ""
    gender: str = ""
    givenName: str = "" # usually the first name
    homeLocation: str = ""  #this should be a list
    honorificPrefix: str = "" #An honorific prefix preceding a Person's name such as Dr/Mrs/Mr.  #this should be a list
    honorificSuffix: str = "" #An honorific suffix following a Person's name such as M.D./PhD/MSCSW.  #this should be a list
    jobTitle: str = ""  #this should be a list
    nationality: str = "" # we can later link it to country   #this should be a list
    workLocation: str = ""  #this should be a list
    worksFor: Organization = None  #this should be a list

    def __post_init__(self):
    # Loop through the fields
        for field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)

Organization.founder = List[Person]
# Organization.funder = Union[Organization(), Person()]
Organization.parentOrganization = Organization()

@dataclass
class CreativeWork(thing):
    abstract: str = ""
    alternativeHeadline: str = ""
    author: List[Union[Organization, Person]] = field(default_factory=list)
    citation: str = "" # this should actually reference to articles
    countryOfOrigin: str = ""
    creativeWorkStatus: str = ""
    dateCreated: str = ""
    dateModified: str = ""
    datePublished: str = ""
    encoding_contentUrl: str = "" 
    encodingFormat: str = ""
    funder: Union[Organization, Person] = None # Organization | Person # we can use pipe operator for Union in Python >= 3.10 
    funding: str = "" # we can change this to Grant
    genre: str = ""
    headline: str = ""
    inLanguage: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    license: str = "" # url or license type
    publication: str = "" #publication event
    publisher: Union[Organization, Person] = None
    sourceOrganization: Organization = None
    sponsor: Union[Organization, Person] = None
    text: str = ""
    thumbnail: str = "" #ImageObject
    thumbnailUrl: str = "" #url
    version: str = ""   

    def __post_init__(self):
    # Loop through the fields
        for field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)


@dataclass
class Article(CreativeWork):    
    articleBody: str = ""
    pageEnd: str = ""
    pageStart: str = ""
    pagination: str = ""
    wordCount: str = ""

    def __post_init__(self):
    # Loop through the fields
        for field in fields(self):
            # If there is a default and the value of the field is none we can assign a value
            if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)


@dataclass
class Dataset(CreativeWork): 
    distribution: str = "" # can be DataDownload
    issn: str = "" #it can be the unique ID of dataset

    def __post_init__(self):
        # Loop through the fields
            for field in fields(self):
                # If there is a default and the value of the field is none we can assign a value
                if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                    setattr(self, field.name, field.default)


#The 'Project' is a new addition to schema.org, and as of now, there are no defined properties for it
@dataclass
class Project(Organization): 
    date_start: str = ""
    date_end: str = ""
    abstract: str = ""

    def __post_init__(self):
        # Loop through the fields
            for field in fields(self):
                # If there is a default and the value of the field is none we can assign a value
                if not isinstance(field.default, dataclasses._MISSING_TYPE) and getattr(self, field.name) is None:
                    setattr(self, field.name, field.default)


@dataclass
class Zenodo:
    resource_type: str
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
    description: str
    author: str


@dataclass
class Institute:
    name: str
    id: str
    country: str
    institute_type: str
    acronyms_name: str
    homepage_url: str
    description: str



@dataclass
class Presentation:
    title: str
    url: str
    authors: str
    description: str
    date: str


@dataclass
class Poster:
    title: str
    url: str
    authors: str
    description: str
    date: str


# @dataclass
# class Dataset:
#     title: str
#     url: str
#     authors: str
#     description: str
#     date: str


@dataclass
class Software:
    title: str
    url: str
    date: str
    authors: str
    description: str
    version: str


@dataclass
class Image:
    title: str
    authors: str
    url: str
    date: str


@dataclass
class Video:
    title: str
    url: str
    authors: str
    date: str


@dataclass
class Lesson:
    title: str
    url: str
    authors: str
    description: str
    date: str

    
@dataclass
class Publisher:
    id: str
    name: str
    homepage_url: str
    country_codes: str
    works_count: str
    h_index: str
    description: str


@dataclass
class Funder:
    name: str
    id: str
    description: str
    country_code: str
    grants_count: str
    homepage_url: str
    works_count: str


@dataclass
class Gesis:
    resource_type: str
    url: str
    date: str 
    title: str
    description: str
    authors: str


# @dataclass
# class Cordis:
#     id: str
#     url: str
#     date: str 
#     title: str
#     description: str


@dataclass
class Orcid:
    id: str
    url: str
    name: str


@dataclass
class Gepris:
    url: str
    title: str
    description: str
    date: str
    applicant_or_leader:str
