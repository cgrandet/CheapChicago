import json
import argparse
import json
import pprint
import sys
import urllib
import urllib2

import oauth2

# with open('categories.json') as f:
# 	categories = json.load(f)

# us_categories = []

# for elem in categories:
# 	if 'US' in elem.get('country_whitelist', []):
# 		us_categories.append(elem) #now we have a list of categories in the US


# sed -i2 's/true/True/g' untitled.txt

def get_business_info(list_of_business_ids):
	'''
	Takes a list of business id's (e.g. ['the-promontory-chicago']) and
	returns a dictionary with the business id's as keys and the Yelp API
	query as their corresponding values
	'''
	query_dict = {}

	for business in list_of_business_ids:
		query_dict[business] = get_business(business)
        print(query_dict[business]["location"])
        print("Loading ..")

	return query_dict


### Author: Ken Mitton (Yelp)
### kmitton@yelp.com 
### https://github.com/Yelp/yelp-api/blob/master/v2/python/sample.py

API_HOST = 'api.yelp.com'
SEARCH_LIMIT = 20
BUSINESS_PATH = '/v2/business/'

# OAuth credential placeholders that must be filled in by users.
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

if __name__=="__main__":
    num_args = len(sys.argv)

    # b_list = ['the-promontory-chicago', 'cafe-53-chicago']
    b_list = ['the-promontory-chicago']
    query = get_business_info(b_list)

    print(query.keys())


