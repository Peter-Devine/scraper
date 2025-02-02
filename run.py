import pandas as pd
from tqdm import tqdm
import json
import os
import argparse

from utils import initialize_driver, does_element_exist, get_attribute, get_text, click_element, click_elements, scroll, get_post_links, get_post_data, is_string_url


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

url = args.page_url
cutoff_date = args.cutoff_date

def get_all_page_data(url, is_community=False):

    name = url.split("/")[-1] if len(url.split("/")[-1]) > 0 else url.split("/")[-2]

    if is_community:
        name = os.path.join(name, "community")
        url = url + "/community"

    data_path = os.path.join(".", "data")
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    page_data_path = os.path.join(data_path, name)
    if not os.path.exists(page_data_path):
        os.mkdir(page_data_path)

    should_scrape_headless = is_community == False
    driver = initialize_driver(args.chrome, args.windows, is_headless=should_scrape_headless)

    driver.get(url)

    page_name = get_text(driver, './/a[@class="_64-f"]')

    print(f"Scrolling {url} until {cutoff_date}")

    scroll(driver, pd.to_datetime(cutoff_date))

    posts = driver.find_elements_by_xpath('//div[contains(@class, "userContentWrapper")]')

    post_links = [get_post_links(post) for post in tqdm(posts)]

    post_links = list(set(post_links))

    with open(os.path.join(page_data_path, 'post_links.json'), 'w') as f:
        json.dump(post_links, f)

    driver.quit()

    print(f"Now scraping {len(post_links)} posts from {name}")

    for i, post_link in enumerate(post_links):

        if not is_string_url(post_link):
            continue

        print(f"Scraping {post_link}")

        driver = initialize_driver(args.chrome, args.windows)

        driver.get(post_link)

        if "/videos/" in post_link:
            post_type = "videos"
        elif "/photos/" in post_link:
            post_type = "photos"
        elif "/posts/" in post_link:
            post_type = "posts"
        elif "/notes/" in post_link:
            post_type = "notes"
        else:
            post_type = "other"

        if post_type == "notes":
            post_element = driver.find_element_by_xpath('.//div[contains(@class, "fb_content")]')
        else:
            post_element = driver.find_element_by_xpath('.//div[contains(@class, "userContentWrapper")]')

        post_data = get_post_data(driver, post_element, post_type)

        post_data["page_name"] = page_name

        with open(os.path.join(page_data_path, f'page_post_{i}.json'), 'w') as f:
            json.dump(post_data, f)

        driver.quit()

    if not is_community:
        get_all_page_data(url, is_community=True)

get_all_page_data(url)
