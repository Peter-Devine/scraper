import pandas as pd
from tqdm import tqdm
import json
import os
import argparse

from utils import initialize_driver, does_element_exist, get_attribute, get_text, click_element, click_elements, scroll, get_post_links, get_post_data


parser = argparse.ArgumentParser()
# parser.add_argument("--from_scratch", type=bool, nargs='?', const=True, default=False,
#                     help="Get list of apps from scratch (I.e. dont download them)")
parser.add_argument("--chrome", type=bool, nargs='?', const=True, default=False,
                    help="Run on chrome?")
parser.add_argument("--windows", type=bool, nargs='?', const=True, default=False,
                    help="Is this script running on windows?")
parser.add_argument('--page_url', required=True)
parser.add_argument('--cutoff_date', required=True)
args = parser.parse_args()



data_path = os.path.join(".", "data")
if not os.path.exists(data_path):
    os.mkdir(data_path)

post_data_path = os.path.join(data_path, "posts")
if not os.path.exists(post_data_path):
    os.mkdir(post_data_path)


driver = initialize_driver(args.chrome, args.windows)

url = args.page_url

driver.get(url)

cutoff_date = args.cutoff_date

print(f"Scrolling {url} until {cutoff_date}")

scroll(driver, pd.to_datetime(cutoff_date))

posts = driver.find_elements_by_xpath('//div[contains(@class, "userContentWrapper")]')

post_links = [get_post_links(post) for post in tqdm(posts)]

with open(os.path.join(data_path, 'post_links.json'), 'w') as f:
    json.dump(post_links, f)

driver.quit()

for i, post_link in tqdm(enumerate(post_links)):
    driver = initialize_driver(True, True)

    driver.get(post_link)

    post_element = driver.find_element_by_xpath('.//div[contains(@class, "userContentWrapper")]')

    post_data = get_post_data(driver, post_element)

    with open(os.path.join(post_data_path, f'{i}.json'), 'w') as f:
        json.dump(post_data, f)

    driver.quit()
