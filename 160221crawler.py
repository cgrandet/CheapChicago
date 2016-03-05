# v 0.1 for Python 2.7
# Carlos O. Grandet Caballero
# Hector Salvador Lopez

import re
from bs4 import BeautifulSoup
import Queue
import json
import sys
import csv
import argparse
import pprint
import urlparse
import urllib
import urllib2
import requests
import datetime

import oauth2

INITIAL_WEBSITE = "http://www.yelp.com/"

TYPE_ESTABLISHMENT = ["Active Life", "Arts & Entertainment", "Automotive", "Beauty & Spas", "Education", 
                    "Event Planning & Services","Financial Services","Food","Health & Medical", "Home Services",
                    "Hotels & Travel","Local Flavor","Local Services","Mass Media","Nightlife","Pets",
                    "Professional Services", "Public Services & Government", "Real Estate", 
                    "Religious Organizations","Restaurants","Shopping"]
NEIGHBORHOOD = []

CRITERIA = {"neighborhood": "Hyde Park", "establishment": "food", "price_range": "1"}

biz = "http://www.yelp.com/biz/harper-cafe-chicago"
url_set = set()
attribute_set = set()

def get_soup(url, url_set):
    html = urllib.urlopen(url).read()
    soup = BeautifulSoup(html,"html.parser")
    url_set.add(url) 
    return soup

def create_website(criteria):
    '''
    Creates the first website url to crawl based on neighborhood, type of 
        establishment, and price range 
    Input: criteria - a dictionary with three keys indicating neighborhood, 
        type of establishment, and price range
    Output: a website url 
    '''
    neighborhood = criteria["neighborhood"].split()
    establishment = criteria["establishment"]
    price_range = criteria["price_range"]
    basic_url = "http://www.yelp.com/search?"
    neighborhood_url = "find_loc={x},+Chicago,+IL&start=0&".format(x = "+".join(neighborhood))
    establishment_url = "sortby=rating&cflt={x}&attrs=Restaurants".format(x = establishment)
    price_url = "PriceRange2.{x}".format(x = price_range)
    final_url = basic_url + neighborhood_url + establishment_url + price_url
    return final_url

def add_links(tag, url_queue, url_set):
    url = tag.get("href")
    url = remove_fragment(url)
    url = convert_if_relative_url("http://www.yelp.com/", url)
    print(url)
    if url != None and url not in url_set: 
        url_queue.put(url)

def add_business_urls(soup, url_queue, url_set):
    biz_tags = soup.find_all("a", class_= "biz-name")
    if biz_tags == None:
        print("not a result page")
        return None
    for tag in biz_tags:
        # biz_name = re.search('(?![biz])[A-Za-z0-9-]+',biz_url)
        # list_biz.append(biz_name.group(0))
        add_links(tag, url_queue, url_set)

def add_additional_pages_urls(soup, url_queue, url_set):
    result_tag = soup.find_all("a", class_ = "available-number pagination-links_anchor")
    if result_tag == None:
        print("link not available")
        return None
    for tag in result_tag:
        add_links(tag, url_queue, url_set)

    # return list_biz

def get_biz_info(soup, url_set, attr_set):
    main_tag = soup.find("div", class_= "biz-page-header-left")
    if main_tag == None:
        print("not a business page")
        return None
    biz_dict = {}
    
    #Get main attributes of business
    price = main_tag.find("span", class_ = "business-attribute price-range").text
    biz_dict["price"] = price
    number_of_reviews = main_tag.find("span", itemprop = "reviewCount").text
    biz_dict["number_of_reviews"] = number_of_reviews
    rating = main_tag.find("meta", itemprop = "ratingValue").get("content")
    biz_dict["rating"] = rating
    
    #Get opening and closing times
    hours_tag = soup.find("table", class_ = "table table-simple hours-table")
    time_dict = {}
    if hours_tag != None:
        for tag in hours_tag.find_all("tr"):
            day = tag.find("th").text
            hours_list = []
            for time in tag.find("td").find_all("span"):
                #hours_list.append(datetime.datetime.strptime(time.text, "%I:%M %p")) Cambio para Json file
                hours_list.append(time.text)
            time_dict[day] = hours_list
        biz_dict["times"] = time_dict
        
    #Get attributes
    attribute_tag = soup.find("div",class_ = "short-def-list").find_all("dl")
    attribute_dict = {} 
    if attribute_tag != None:
        for tag in attribute_tag:
            attr_title = re.search("[A-Za-z].+",tag.find("dt").text).group(0)
            attr_desc = re.search("[A-Za-z].+",tag.find("dd").text).group(0)
            attribute_dict[attr_title] = attr_desc 
            attr_set.add((attr_title, attr_desc))
        biz_dict["attributes"] = attribute_dict
    

    comment_tag = soup.find_all("div", class_ = "review-content")
    if comment_tag != None:
        comment_dict = {}
        for i, tag in enumerate(comment_tag):
            description = tag.find("p", itemprop = "description").text
            rating = re.search("\d", tag.find("i").get("title")).group(0)
            date_list = tag.find("meta", itemprop = "datePublished").get("content").split("-")
            date_list = [int(i) for i in date_list]
            date = datetime.date(date_list[0],date_list[1],date_list[2])
            comment_dict[i] = {"description" : description, "rating" : rating, \
            "date" : date_list} #Cambio para hacerlo JSON
        biz_dict["comments"] = comment_dict

    return biz_dict

    #Get comments
    # comment_queue = queue.Queue()
    # add_additional_pages_urls(soup,comment_queue,url_set)
    # while not comment_queue.empty():
    #     soup = get_soup(current_url,url_set)

def get_comments(soup, biz_dict):    
    comment_tag = soup.find_all("div", class_ = "review-content")
    if comment_tag != None:
        comment_dict = {}
        for i, tag in enumerate(comment_tag):
            description = tag.find("p", itemprop = "description").text
            rating = re.search("\d", tag.find("i").get("title")).group(0)
            date_list = tag.find("meta", itemprop = "datePublished").get("content").split("-")
            date_list = [int(i) for i in date_list]
            date = datetime.date(date_list[0],date_list[1],date_list[2])
            comment_dict[i] = {"description" : description, "rating" : rating, \
            "date" : date}
        biz_dict["comments"] = comment_dict

    return biz_dict

# Por que este get_comments y el ultimo pedazo del codigo anterior?
# Son iguales...

def run_model(criteria, num_pages_to_crawl):
    original_url = create_website(criteria)
    url_set = set()
    url_queue = Queue.Queue()
    url_queue.put(original_url)

    establishments_list = []
    establishments_dict = {}
    api_dict = {}
    attributes_set = set()
    
    while not url_queue.empty() and len(url_set) <= num_pages_to_crawl:
        current_url = url_queue.get()
        soup = get_soup(current_url, url_set)
        print(current_url)
        biz_dict = get_biz_info(soup, url_set, attributes_set)
        #biz_id = re.search("(biz/)(.+)(\?*)", current_url).group(2)
        if biz_dict != None:
        #if biz_dict != None and establishments_dict[biz_id]:
            biz_id = re.search("(biz/)(.+)(\?*)", current_url).group(2)
            print(biz_id)
            establishments_dict[biz_id] = biz_dict
            api_dict[biz_id] = get_business(biz_id)
            biz_dict["categories"] = api_dict[biz_id]["categories"]
            biz_dict["address"] = api_dict[biz_id]["location"]["address"]
            biz_dict["neighborhoods"] = api_dict[biz_id]["location"]["neighborhoods"]
            biz_dict["latitude"] = api_dict[biz_id]["location"]["coordinate"]["latitude"]
            biz_dict["longitude"] = api_dict[biz_id]["location"]["coordinate"]["longitude"]
            print(len(url_set))
        else: 
            add_business_urls(soup, url_queue, url_set)
            add_additional_pages_urls(soup, url_queue, url_set)

    with open('establishments_dict.json', 'w') as f:
        json.dump(establishments_dict, f)

    attributes_set_dict = {}
    for key, value in list(attributes_set):
        attr_list = attributes_set_dict.get(key,[])
        attr_list.append(value)
        attributes_set_dict[key] = attr_list

    with open('attributes_dict.json', 'w') as a:
        json.dump(attributes_set_dict, a)


def is_absolute_url(url):
    '''
    Is url an absolute URL?
    '''
    if len(url) == 0:
        return False
    return len(urlparse.urlparse(url).netloc) != 0


def remove_fragment(url):
    '''remove the fragment from a url'''
    (url, frag) = urlparse.urldefrag(url)
    return url


def convert_if_relative_url(current_url, new_url):
    '''
    Attempt to determine whether new_url is a relative URL and if so,
    use current_url to determine the path and create a new absolute
    URL.  Will add the protocol, if that is all that is missing.

    Inputs:
        current_url: absolute URL
        new_url: 

    Outputs:
        new absolute URL or None, if cannot determine that
        new_url is a relative URL.

    Examples:
        convert_if_relative_url("http://cs.uchicago.edu", "pa/pa1.html") yields 
            'http://cs.uchicago.edu/pa/pa.html'

        convert_if_relative_url("http://cs.uchicago.edu", "foo.edu/pa.html") yields
            'http://foo.edu/pa.html'
    '''
    if len(new_url) == 0 or not is_absolute_url(current_url):
        return None

    if is_absolute_url(new_url):
        return new_url

    parsed_url = urlparse.urlparse(new_url)
    path_parts = parsed_url.path.split("/")

    if len(path_parts) == 0:
        return None

    ext = path_parts[0][-4:]
    if ext in [".edu", ".org", ".com", ".net"]:
        return parsed_url.scheme + new_url
    elif new_url[:3] == "www":
        return parsed_url.scheme + new_path
    else:
        return urlparse.urljoin(current_url, new_url)

##################################
### Author: Ken Mitton (Yelp)   ##
### kmitton@yelp.com            ##
### https://github.com/Yelp/yelp-api/blob/master/v2/python/sample.py
##################################

API_HOST = 'api.yelp.com'
SEARCH_LIMIT = 20
BUSINESS_PATH = '/v2/business/'

CONSUMER_KEY = 'dStcfiGFCoZkOlva9XeZtA'
CONSUMER_SECRET = 'WoJ9LxTFCVgdYFq6yn3GAlLRRXE'
TOKEN = 'VnMH3YjeyYcvV4mhXVzfcJhOwRNgaBFX'
TOKEN_SECRET = 'boGGX7K0aX2gcY39kF3uAwuEdu0'

def request(host, path, url_params=None):
    """Prepares OAuth authentication and sends the request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        urllib2.HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = 'https://{0}{1}?'.format(host, urllib.quote(path.encode('utf8')))

    consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    oauth_request = oauth2.Request(
        method="GET", url=url, parameters=url_params)

    oauth_request.update(
        {
            'oauth_nonce': oauth2.generate_nonce(),
            'oauth_timestamp': oauth2.generate_timestamp(),
            'oauth_token': TOKEN,
            'oauth_consumer_key': CONSUMER_KEY
        }
    )
    token = oauth2.Token(TOKEN, TOKEN_SECRET)
    oauth_request.sign_request(
        oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
    signed_url = oauth_request.to_url()

    print u'Querying {0} ...'.format(url)

    conn = urllib2.urlopen(signed_url, None)
    try:
        response = json.loads(conn.read())
    finally:
        conn.close()

    return response

def get_business(business_id):
    """Query the Business API by a business ID.
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """
    business_path = BUSINESS_PATH + business_id

    return request(API_HOST, business_path)

################################
################################


if __name__=="__main__":

    run_model(CRITERIA, 20)


# soup = get_soup(biz,url_set)
# establishments_dict = get_biz_info(soup, url_set, attribute_set)
# with open('establishments_dict.json', 'w') as f:
#         json.dump(establishments_dict, f)

# def add_urls_from_website(object_soup, url_queue, parent_url, url_set):
#     '''
#     get all the urls linked to a website and add them to a 
#     queue of websites to follow. 

#     Inputs:
#         object_soup : a Beautiful Soup object
#         url_queue : a queue of websites to visit 
#         parent_url: the parent url from which you are crawling
#         url_set: a set of visited urls 

#     Outputs: 
#         None. Adds urls to the provided url_queue
#     '''
#     a_tags = object_soup.find_all("a","")
#     for tag in a_tags:
#         tag_url = tag.get("href", "fake_website")
#         if not util.is_absolute_url(tag_url):
#             tag_url = util.remove_fragment(tag_url)
#             tag_url = util.convert_if_relative_url(parent_url, tag_url)
        
#         if tag_url != None and tag_url not in url_set and \
#             util.is_url_ok_to_follow(tag_url, LIMITING_DOMAIN): 
#             url_queue.put(tag_url)


# def go(num_pages_to_crawl, course_map_filename, index_filename):
#     '''
#     Crawl the college catalog and generates a CSV file with an index.

#     Inputs:
#         num_pages_to_crawl: an integer, the number of pages to process during 
#             the crawl
#         course_map_filename: a string with the name of a JSON file that contains
#             the mapping course codes to course identifiers
#         index_filename: a string with the name for the CSV of the index

#     Outputs: 
#         CSV file of the index
#     '''

#     course_index = crawl_website(STARTING_URL, LIMITING_DOMAIN, num_pages_to_crawl)
#     gen_csv_file(course_index, course_map_filename, index_filename)

#     return course_index


# def crawl_website(initial_url, limiting_domain, num_pages_to_crawl):
#     '''
#     Inputs:
#         initial_url: a string with the initial url to follow
#         limiting_domain: a string with the domain where the crawling should
#             be limited to
#         num_pages_to_crawl: an integer to restrict the maximum number of
#             visited pages

#     Output:
#         course_index: a dictionary with the course id's of the College 
#             catalog as keys and their descriptions as items
#     '''

#     url_queue = queue.Queue() 
#     url_visits = set() 
#     course_index = {}

#     url_queue.put(initial_url)
#     while not url_queue.empty() and len(url_visits) <= num_pages_to_crawl:
#         website = url_queue.get()
#         if website not in url_visits:
#             url_visits.add(website)
#             website_soup = get_website_soup(website, url_visits)
#             if website_soup == None:
#                 pass
#             else:
#                 add_urls_from_website(website_soup, url_queue, website, url_visits)
#                 gen_course_dictionary(website_soup, course_index)

#     return course_index


# def get_website_soup(url, url_set): 
#     '''
#     get website url as a beautiful soup object

#     Inputs:
#         url: string representing absolute url of a website 
#         url_set: a set with the urls that have already been visited

#     Outputs: 
#         HTML beautiful soup object
#     '''
#     if len(url) == 0:
#         print("url not absolute")
#         return None

#     else:   
#         request_attempts = 0 
#         # Try 3 times to get information from a site 
#         while request_attempts <= 3:
#             url_object = util.get_request(url)
#             if url_object == None:
#                 request_attempts += 1
#             elif url_object == None and request_attemtps == 3:
#                 print("request failed")
#                 return url_object

#             #Read object and get Beautiful Soup object
#             else: 
#                 object_text = util.read_request(url_object)
#                 object_url = util.get_request_url(url_object)
#                 url_set.add(object_url) 
#                 object_soup = bs4.BeautifulSoup(object_text, "html5lib")
#                 return object_soup


# def add_urls_from_website(object_soup, url_queue, parent_url, url_set):
#     '''
#     get all the urls linked to a website and add them to a 
#     queue of websites to follow. 

#     Inputs:
#         object_soup : a Beautiful Soup object
#         url_queue : a queue of websites to visit 
#         parent_url: the parent url from which you are crawling
#         url_set: a set of visited urls 

#     Outputs: 
#         None. Adds urls to the provided url_queue
#     '''
#     a_tags = object_soup.find_all("a")
#     for tag in a_tags:
#         tag_url = tag.get("href", "fake_website")
#         if not util.is_absolute_url(tag_url):
#             tag_url = util.remove_fragment(tag_url)
#             tag_url = util.convert_if_relative_url(parent_url, tag_url)
        
#         if tag_url != None and tag_url not in url_set and \
#             util.is_url_ok_to_follow(tag_url, LIMITING_DOMAIN): 
#             url_queue.put(tag_url)


# def gen_course_dictionary(object_soup, course_index):
#     '''
#     get the title of a course and add it as a key to the dictionary
#     and adds the course description as value

#     Inputs:
#         object_soup : a Beautiful Soup object
#         course_index : a dictionary relating a course with words  

#     Outputs: 
#         None. Updates the provided dictionary 
#     '''

#     div_tags = object_soup.find_all("div", class_ = "courseblock main")
#     if len(div_tags) != 0:
#         for tag in div_tags:
            
#             # Get the course title and add it as a key
#             title_tags = tag.find("p", class_ = "courseblocktitle")
#             title_string = title_tags.text 
#             title_string.replace("&#160;"," ")
#             course_id = re.search("\w* [0-9]*", title_string.replace("\xa0", \
#                 " ")).group()
#             course_index[course_id] = course_index.get(course_id, [])

#             # Get the words of the course title and description and add each as
#             # a value in a list
#             course_title_words = re.findall('[a-zA-Z][a-zA-Z0-9]+', title_string)
#             desc_tags = tag.find("p", class_ = "courseblockdesc")
#             desc_string = desc_tags.text
#             desc_words = re.findall("[a-zA-Z][a-zA-Z0-9]+", desc_string)
#             list_words = desc_words + course_title_words
            
#             list_sequences = util.find_sequence(tag)
#             if len(list_sequences) != 0:
#                 for seq in list_sequences:
#                     stitle_tags = seq.find("p", class_ = "courseblocktitle")
#                     stitle_string = stitle_tags.text 
#                     stitle_string.replace("&#160;", " ")
#                     scourse_id = re.search("\w* [0-9]*", \
#                         stitle_string.replace("\xa0", " ")).group()
#                     course_index[scourse_id] = course_index.get(scourse_id, [])
#                     sdesc_tags = seq.find("p", class_ = "courseblockdesc")
#                     sdesc_string = sdesc_tags.text
#                     slist_words = re.findall("[a-zA-Z][a-zA-Z0-9]+", sdesc_string)
#                     final_list_words = slist_words + list_words
#                     for word in final_list_words:
#                         if word.lower() not in INDEX_IGNORE and word.lower() \
#                         not in course_index[scourse_id]:
#                             course_index.get(scourse_id).append(word.lower()) 
#             else:          
#                 for word in list_words:
#                     if word.lower() not in INDEX_IGNORE and word.lower() \
#                     not in course_index[course_id]:
#                         course_index.get(course_id).append(word.lower()) 
            
    

# def gen_csv_file(course_index, course_map_filename,index_filename):
#     '''
#     This function generates a CSV file with course ID and the words
#     associated to that course ID

#     Inputs:
#         course_index: a dictionary linking courses to words
#         course_map_filename: a JSON file
#         index_filename: the name of the CSV file 

#     Outputs:
#         A CSV file
#     '''

#     with open(course_map_filename) as map_filename:   
#         json_data = json.load(map_filename)

#     with open(index_filename, "w") as csv_file:
#         writer = csv.writer(csv_file, delimiter = '|')
#         for course_title in list(course_index.keys()):
#             for word in course_index[course_title]:
#                 course_code = json_data[course_title] 
#                 writer.writerow([course_code, word])

#     return index_filename


# if __name__ == "__main__":
#     usage = "python3 crawl.py <number of pages to crawl>"
#     args_len = len(sys.argv)
#     course_map_filename = "course_map.json"
#     index_filename = "catalog_index.csv"
#     if args_len == 1:
#         num_pages_to_crawl = 1000
#     elif args_len == 2:
#         try:
#             num_pages_to_crawl = int(sys.argv[1])
#         except ValueError:
#             print(usage)
#             sys.exit(0)
#     else:
#         print(usage)    
#         sys.exit(0)

#     go(num_pages_to_crawl, course_map_filename, index_filename)
