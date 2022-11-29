class Person:
  def __init__(self, name, URL):
    self.name = name
    self.URL = URL

class Article:
  def __init__(self, title, URL, authors, date):
    self.title = title
    self.URL = URL
    self.authors = authors
    self.date = date

class Zenodo:
  def __init__(self, id, type, URL):
    self.id = id
    self.type = type
    self.URL = URL