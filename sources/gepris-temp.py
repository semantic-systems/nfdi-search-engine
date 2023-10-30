import requests
import logging
from bs4 import BeautifulSoup
def find_organization(id):
                    # Find the organization's address details within the div with id "address_data" 
                    url_address_details=f'https://gepris.dfg.de/gepris/institution/{id}?context=institution&task=showDetail&id={id}'
                    response = requests.get(url_address_details)
                    response.raise_for_status()
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        address_data = soup.find("div", id="address_data")
                        if address_data:
                            address_span = address_data.find("span", class_="value")
                            if address_span:
                                address = '\n'.join([line.strip() for line in address_span.stripped_strings])
                                print("ID of organization:", id)
                                print("Address:", address)
                                print()
                            else:
                                address = "Address not found."
                        else:
                            print("Address data not found")
                       
                        sub_organization = soup.find("div", id="untergeordneteInstitutionen")
                        if sub_organization:
                            for sub_org in sub_organization.find_all("li"):
                                sub_org_id = sub_org.get("id")
                                sub_org_url = 'https://gepris.dfg.de/gepris/institution/' + sub_org_id
                                sub_org_name = sub_org.find("a").text.strip()
                                print("Sub-org-ID:", sub_org_id)
                                print("sub-org-url:", sub_org_url)
                                print("sub-org-name:", sub_org_name)
                                print()
                        else:
                            print("Sub organizations not available.")
                        sub_project = soup.find("div", id="beteiligungen-main")
                        if sub_project:
                            for sub_proj in sub_project.find_all("a", class_=["intern", "hrefWithNewLine"]):
                                if "intern" in sub_proj.get("class", []) and "hrefWithNewLine" in sub_proj.get("class", []):
                                    # print("sub projects:", sub_project)
                                    sub_project_link_id = sub_proj["href"]
                                    sub_project_id = sub_project_link_id.split("/")[-1]
                                    sub_project_url = 'https://gepris.dfg.de/gepris/projekt/' + sub_project_id
                                    sub_project_name = sub_proj.text.strip()
                                    print("Sub Project ID:", sub_project_link_id)
                                    print("Sub Projcet ID:", sub_project_id)
                                    print("Sub project URL:", sub_project_url)
                                    print("Sub Project Name:", sub_project_name)
                                    print()
                        else:
                              print("sub project not avialalbe.")
     
find_organization("35962653")