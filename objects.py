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
    identifier: str = "" #doi or pid will be stored as identifier    
    originalSource: str = ""
    source: list() = field(default_factory=list) # this list will have "thing" objects

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
    
Organization.founder = List[Person]  
# Organization.funder = Union[Organization(), Person()]
Organization.parentOrganization = Organization()


@dataclass
class Author(Person):
    # orcid: str = "" # we should not have this attribute; orcid should be kept in 
    works_count: str = ""
    cited_by_count: str = ""

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
@dataclass
class Article(CreativeWork):    
    articleBody: str = ""
    pageEnd: str = ""
    pageStart: str = ""
    pagination: str = ""
    wordCount: str = ""

@dataclass
class Dataset(CreativeWork): 
    distribution: str = ""
    issn: str = ""

#The 'Project' is a new addition to schema.org, and as of now, there are no defined properties for it
@dataclass
class Project(Organization): 
    dateStart: str = ""
    dateEnd: str = ""
    dateLastModified : str = ""
    abstract: str = ""
    inLanguage: List[str] = field(default_factory=list)
    availableLanguages: List[str] = field(default_factory=list)
    objective: str = ""
    status: str = ""
    author: List[Union[Organization, Person]] = field(default_factory=list)
    funder: List[Union[
        Organization, Person]] = field(
        default_factory=list)  # Organization | Person # we can use pipe operator for Union in Python >= 3.10
@dataclass
class SoftwareApplication(CreativeWork):
    distribution: str = ""
    issn: str = ""
@dataclass
class LearningResource(CreativeWork): 
    assesses: str = ""  #The item being described is intended to assess the competency or learning outcome defined by the referenced term.
    competencyRequired: str = ""
    educationalAlignment:str = ""
    educationalLevel:str = ""
    educationalUse:str = ""
    learningResourceType:str = ""
    teaches:str = ""   #The item being described is intended to help a person learn the competency or learning outcome defined by the referenced term.

@dataclass
class MediaObject(CreativeWork): 
    associatedArticle: str = ""
    bitrate: str = ""
    contentSize: str = ""
    contentUrl: str = ""
    duration: str = ""
    embedUrl: str = ""
    encodesCreativeWork: str = ""
    encodingFormat: str = ""
    endTime: str = ""
    height: str = ""
    ineligibleRegion: str = ""
    playerType: str = ""
    productionCompany: str = ""
    regionsAllowed: str = ""
    requiresSubscription: str = ""
    sha256: str = ""
    startTime: str = ""
    uploadDate: str = ""
    width: str = ""
    
@dataclass
class VideoObject(MediaObject): 
    actor: str = ""
    caption: str = ""
    director: str = ""
    embeddedTextCaption: str = ""
    musicBy: str = ""
    transcript: str = ""
    videoFrameSize: str = ""
    videoQuality: str = ""
@dataclass
class ImageObject(MediaObject): 
    caption: str = ""
    embeddedTextCaption: str = ""
    exifData: str = ""  #exif data for this object
    representativeOfPage: str = ""   #Indicates whether this image is representative of the content of the page

@dataclass
class Place(thing): 
    additionalProperty: str = ""
    address: str = ""
    addressType: str = ""
    aggregateRating: str = ""
    amenityFeature: str = ""
    branchCode: str = ""
    containedInPlace: str = ""	
    containsPlace	: str = ""
    event: str = ""
    faxNumber: str = ""
    geo: str = ""
    geoContains: str = ""
    geoCoveredBy: str = ""
    geoCovers: str = ""
    geoCrosses: str = ""
    geoDisjoint: str = ""
    geoEquals: str = ""
    geoIntersects: str = ""
    geoOverlaps: str = ""
    geoTouches: str = ""
    geoWithin: str = ""
    globalLocationNumber: str = ""	
    hasDriveThroughService: str = ""
    hasMap: str = ""
    isAccessibleForFree: str = ""	
    isicV4: str = ""
    keywords: str = ""
    latitude: str = ""
    licence: str = ""
    logo: str = ""
    longitude: str = ""
    maximumAttendeeCapacity: str = ""	
    openingHoursSpecification: str = ""
    photo: str = ""
    placType: str = ""
    publicAccess: str = ""
    review: str = ""
    slogan: str = ""
    smokingAllowed: str = ""
    specialOpeningHoursSpecification: str = ""
    telephone: str = ""
    tourBookingPage: str = ""

#################################################################################
# classes defined below should not be used, as they are not mapped to schema.org
# ###############################################################################

@dataclass
class Zenodo:
    resource_type: str
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
    description: str
    author: str

# @dataclass
# class Zenodo:
#     resource_type: str
#     url: str
#     date: str  # e.g. '2022-07-06'
#     title: str
#     description: str
#     author: str

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


'''
@dataclass
class Software:
    title: str
    url: str
    date: str
    authors: str
    description: str
    version: str
'''


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


@dataclass
class Cordis:
    id: str
    url: str
    date: str 
    title: str
    description: str


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
