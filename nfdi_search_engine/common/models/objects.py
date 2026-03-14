from typing import Union, List
from pydantic.dataclasses import dataclass
from pydantic import Field, BaseModel
from dataclasses import fields

class thing(BaseModel):
    name: str = ""
    alternateName: List[str] = Field(default_factory=list)
    description: str = ""
    url: str = ""
    image: str = "" #url of the image
    identifier: str = "" #doi or pid will be stored as identifier   
    additionalType: str = "" 
    originalSource: str = ""
    source: List["thing"] = Field(default_factory=list) # this list will have "thing" objects
    rankScore: float = 0 #bm25 ranking score for sorting the search results
    partiallyLoaded: bool = False

    # @classmethod
    def __str__(self):
        strValue = ""
        for field in self.model_fields.keys():
            # print(field.type)
            # concatenate all the property values            
            strValue += f"{getattr(self, field)}###"
        return strValue
    
    def __hash__(self):
        return hash((self.identifier, self.name, self.url, self.originalSource))


class Organization(thing):
    address: str = ""
    email: str = ""
    legalName: str = ""
    location: str = ""
    logo: str = "" # url
    numberOfEmployees: str = ""
    telephone: str = ""
    foundingDate: str = ""
    keywords: List[str] = Field(default_factory=list)

class Person(thing):
    additionalName: str = ""
    address: str = "" #this should be a list
    affiliation: List[Organization] = Field(default_factory=list)  #this should be a list
    alumniOf: List[Organization] = Field(default_factory=list)  #this should be a list
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



class CreativeWork(thing):
    abstract: str = ""
    alternativeHeadline: str = ""
    author: List[Union[Organization, Person]] = Field(default_factory=list)
    citation: List["CreativeWork"] = Field(default_factory=list) # this list will have "CreativeWork" objects
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
    inLanguage: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    license: str = "" # url or license type
    publication: str = "" #publication event
    publisher: Union[Organization, Person] = None
    sourceOrganization: Organization = None
    sponsor: Union[Organization, Person] = None
    text: str = ""
    thumbnail: str = "" #ImageObject
    thumbnailUrl: str = "" #url
    version: str = ""


class Article(CreativeWork):
    articleBody: str = ""
    pageEnd: str = ""
    pageStart: str = ""
    pagination: str = ""
    wordCount: str = ""
    referenceCount: str = ""
    citationCount: str = ""
    reference: List[Union["Article", CreativeWork]] = Field(default_factory=list) # this list will have "CreativeWork" or "Article" objects


class Dataset(CreativeWork): 
    distribution: str = ""
    issn: str = ""


class Author(Person):    
    works_count: str = ""
    about: str = ""
    banner: str = ""
    cited_by_count: str = ""    
    researchAreas: List[str] = Field(default_factory=list)
    works: List[Union[Article, Dataset]] = Field(default_factory=list)

#The 'Project' is a new addition to schema.org, and as of now, there are no defined properties for it

class Project(CreativeWork): 
    dateStart: str = ""
    dateEnd: str = ""   
    duration: str = "" 
    status: str = ""   
    currency: str = ""
    totalCost: str = ""
    fundedAmount: str = ""
    eu_contribution: str = ""     

class SoftwareApplication(CreativeWork):
    distribution: str = ""
    issn: str = ""

class LearningResource(CreativeWork): 
    assesses: str = ""  #The item being described is intended to assess the competency or learning outcome defined by the referenced term.
    competencyRequired: str = ""
    educationalAlignment:str = ""
    educationalLevel:str = ""
    educationalUse:str = ""
    learningResourceType:str = ""
    teaches:str = ""   #The item being described is intended to help a person learn the competency or learning outcome defined by the referenced term.


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
    

class VideoObject(MediaObject): 
    actor: str = ""
    caption: str = ""
    director: str = ""
    embeddedTextCaption: str = ""
    musicBy: str = ""
    transcript: str = ""
    videoFrameSize: str = ""
    videoQuality: str = ""

class ImageObject(MediaObject): 
    caption: str = ""
    embeddedTextCaption: str = ""
    exifData: str = ""  #exif data for this object
    representativeOfPage: str = ""   #Indicates whether this image is representative of the content of the page


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


class Zenodo:
    resource_type: str
    url: str
    date: str  # e.g. '2022-07-06'
    title: str
    description: str
    author: str

# 
# class Zenodo:
#     resource_type: str
#     url: str
#     date: str  # e.g. '2022-07-06'
#     title: str
#     description: str
#     author: str


class Institute:
    name: str
    id: str
    country: str
    institute_type: str
    acronyms_name: str
    homepage_url: str
    description: str




class Presentation:
    title: str
    url: str
    authors: str
    description: str
    date: str



class Poster:
    title: str
    url: str
    authors: str
    description: str
    date: str


# 
# class Dataset:
#     title: str
#     url: str
#     authors: str
#     description: str
#     date: str


'''

class Software:
    title: str
    url: str
    date: str
    authors: str
    description: str
    version: str
'''



class Image:
    title: str
    authors: str
    url: str
    date: str



class Video:
    title: str
    url: str
    authors: str
    date: str



class Lesson:
    title: str
    url: str
    authors: str
    description: str
    date: str

    

class Publisher:
    id: str
    name: str
    homepage_url: str
    country_codes: str
    works_count: str
    h_index: str
    description: str



class Funder:
    name: str
    id: str
    description: str
    country_code: str
    grants_count: str
    homepage_url: str
    works_count: str



class Gesis:
    resource_type: str
    url: str
    date: str 
    title: str
    description: str
    authors: str



class Cordis:
    id: str
    url: str
    date: str 
    title: str
    description: str



class Orcid:
    id: str
    url: str
    name: str



class Gepris:
    url: str
    title: str
    description: str
    date: str
    applicant_or_leader:str