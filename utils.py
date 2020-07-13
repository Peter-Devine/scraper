import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
import pandas as pd

MAX_SCROLLS_POSSIBLE = 1000

def scroll(driver, end_date, num_scrolls=MAX_SCROLLS_POSSIBLE):

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    time.sleep(0.1)

    WebDriverWait(driver, 7).until(
            EC.invisibility_of_element_located((By.XPATH, "//span[@aria-valuetext=='Loading...']")))

    def get_last_date(position=-1):
        last_post = driver.find_elements_by_xpath('//div[contains(@class, "userContentWrapper")]')[position]
        last_date = get_attribute(last_post, './/span[contains(@class, "timestampContent")]/..', "title")

        if last_date is None:
            return get_last_date(position=position-1)
        else:
            return last_date

    last_date = get_last_date()

    last_date = last_date.replace(" at", "")

    last_date = pd.to_datetime(last_date)

    print(f"Scroll number {num_scrolls} with last date {last_date}")

    if num_scrolls < 0:
        print(f"Stopping scrolling early after {MAX_SCROLLS_POSSIBLE} scrolls with the last date as {last_date}")
        return None

    if last_date > end_date:
        scroll(driver, end_date, num_scrolls=num_scrolls-1)

# Initializes the webdriver for the browser
def initialize_driver(is_chrome, is_windows):

    if is_chrome:
        opts = ChromeOptions()

        # Disable images from loaded pages
        prefs = {"profile.managed_default_content_settings.images": 2}
        opts.add_experimental_option("prefs", prefs)
        driver_name = "chromedriver"
    else:
        opts = FirefoxOptions()

        driver_name = "geckodriver"
    opts.add_argument("--headless")
    opts.add_argument("--width=1920")
    opts.add_argument("--height=1080")

    driver_suffix = ".exe" if is_windows else ""
    driver_path =  os.path.join(os.getcwd(), driver_name+driver_suffix)

    if is_chrome:
        driver = webdriver.Chrome(options=opts, executable_path=driver_path)
    else:
        driver = webdriver.Firefox(options=opts, executable_path=driver_path)
    return driver

def wait_for_element(driver, xpath, time):
    try:
        WebDriverWait(driver, time).until(
                EC.visibility_of_element_located((By.XPATH, xpath)))
        return True
    except Exception:
        return False

# CHeck if element exists
def does_element_exist(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath)
        return True
    except Exception:
        return False

# CHeck if element exists
def get_attribute(driver, xpath, attribute):
    try:
        return driver.find_element_by_xpath(xpath).get_attribute(attribute)
    except Exception:
        return None

# CHeck if element exists
def get_text(driver, xpath):
    try:
        return driver.find_element_by_xpath(xpath).text.strip()
    except Exception:
        return None

# Check if element exists, and click it if it does
def click_element(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath).click()
        return True
    except Exception:
        return False

# Check if element exists, and click it if it does
def click_elements(driver, search_element, xpath):
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.XPATH, "//span[@aria-valuetext=='Loading...']")))

        elements = search_element.find_elements_by_xpath(xpath)[::-1]
        for element in elements:
            driver.execute_script("arguments[0].click();", element)
        return len(elements) > 0
    except Exception as err:
        print(f"Error in clicking multiple {xpath}\n\n\n {err}")
        return True


def get_post_links(post):

    post_link = get_attribute(post, './/a[contains(@class, "_3hg-")]', "href")

    if post_link is None:
        post_link = get_attribute(post, './/span[contains(@class, "timestampContent")]/../..', "href")

    return post_link


def get_post_data(driver, post, post_type):

    wait_for_element(driver, './/a[contains(@class, "_3hg-")]', 10)

    if post_type == "notes":
        date = get_text(post, './/a[contains(@class, "_39g5")]')
        post_text = get_text(post, './/div[contains(@class, "_39k5")]')
    else:
        date = get_attribute(post, './/span[contains(@class, "timestampContent")]/..', "title")
        post_text = get_text(post, './/div[@data-testid="post_message"]')

    is_video = does_element_exist(post, './/div[@data-testid="post_message"]/following-sibling::div//video')

    if is_video:
        is_link = False
        link_destination = None
    else:
        is_link = does_element_exist(post, './/div[@data-testid="post_message"]/following-sibling::div//a')
        link_destination = get_attribute(post, './/div[@data-testid="post_message"]/following-sibling::div//a', "href")

    num_reactions = get_text(post, './/a[@data-testid="UFI2ReactionsCount/root"]/span[2]/span/span')
    num_comments = get_text(post, './/a[contains(@class, "_3hg-")]')
    num_shares = get_text(post, './/a[@data-testid="UFI2SharesCount/root"]')

    # N.B. Comments are already displayed on notes posts
    if not does_element_exist(driver, './/div[@aria-label="Comment"]'):
        click_element(post, './/a[contains(@class, "_3hg-")]')

    wait_for_element(driver, './/div[@aria-label="Comment"]', 5)

    # We scroll to avoid video auto-playing and then automatically going to the next page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    while True:
        original_comments_to_open_num = len(post.find_elements_by_xpath('.//span[contains(@class, "_4ssp")]'))

        print(f"Opening {original_comments_to_open_num} more comments")

        if original_comments_to_open_num < 1:
            break

        is_comments_to_open = click_elements(driver, post, './/span[contains(@class, "_4ssp")]')

        if is_comments_to_open == False:
            break

        i = 80
        while original_comments_to_open_num == len(post.find_elements_by_xpath('.//span[contains(@class, "_4ssp")]')):
            time.sleep(0.1)
            i -= 1
            if i < 0:
                break

    print(f"Expanding comments")
    click_elements(driver, post, './/a[contains(@class, "_5v47")]')

    comments = post.find_elements_by_xpath('.//div[@aria-label="Comment"]')

    comment_data = [get_comment_data(comment) for comment in comments]

    post_link = driver.current_url

    return {
        "post_link": post_link,
        "post_type": post_type,
        "date": date,
        "is_video": is_video,
        "is_link": is_link,
        "post_text": post_text,
        "num_reactions": num_reactions,
        "num_comments": num_comments,
        "num_shares": num_shares,
        "comment_data": comment_data
    }

def get_comment_data(comment, is_reply=False):

    comment_text = get_text(comment, './/span[@dir="ltr"]')
    has_image = does_element_exist(comment, './/div[@class="_2txe"]')
    reactions = get_text(comment, './/span[@class="_1lld"]')
    commenter_name = get_text(comment, './/*[@class="_6qw4"]')

    print(f"Getting comment data from {commenter_name}")

    comment_data = {
        "comment_text": comment_text,
        "commenter_name": commenter_name,
        "has_image": has_image,
        "reactions": reactions,
    }

    if not is_reply:
        replies = comment.find_elements_by_xpath('../..//div[@aria-label="Comment reply"]')
        reply_data = [get_comment_data(reply, is_reply=True) for reply in replies]
        comment_data["replies"] = reply_data

    return comment_data
