#!/usr/bin/env python
# coding: utf-8

# In[119]:


import requests
from bs4 import BeautifulSoup
from collections import deque
import json
from urllib.parse import urljoin, unquote, urlparse
import networkx as nx
import time
import random
import math
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException


# In[2]:


class WebPage():
    def __init__(self, url):
        self.url = url
        self.pagerank_score = None
        self.HITS_score = None
        self.total_score = None


# In[3]:


class SeedPage(WebPage):
    def __init__(self, url):
        super().__init__(url)
        self.dir_graph = nx.DiGraph()
        self.extracted_pages = set()
        self.all_pages = dict()
        self.capacity = 1000
        self.is_rendered = None
    
    def __contains__(self, url):
        for page in self.extracted_pages:
            if url == page.url:
                return True
        return False
    
    def __getitem__(self, x):
        list_ext_pages = list(self.extracted_pages)
        sorted_list_ext_pages = sorted(list_ext_pages, key= lambda x: x.total_score, reverse= True)
        return sorted_list_ext_pages[x]
    
    def save(self, url):
        webpage = WebPage(url)
        self.extracted_pages.add(webapge)
        
    def add(self, url, depth):
        self.all_pages.append({url: depth})


# In[181]:


def go_to_depth(seed_page):
    
    seed_url = seed_page.url
    G = seed_page.dir_graph

    # First json file name
    depth_file_path = urlparse(seed_url).netloc + ".json"

    # Initialize a queue with (URL, depth) tuples
    queue = deque([(seed_url, 0)])

    # new updates for json file
    depth_data = {seed_url: 0}
    new_addings = 1

    while queue:
        url, depth = queue.popleft()

        # Check if the URL's depth reaches 7
        if depth == 2:
            update_jsons(depth_file_path, depth_data)
            calculate_pagerank_scores(seed_page)
            break

        # Fetch the page content
        hyperlinks = find_hyperlinks(url, seed_page, 0)
        print(f"The hyperlinks get from the url {url} are {len(hyperlinks)}")
        for link in hyperlinks:
            print(link)
        for hyperlink in hyperlinks:
            if hyperlink not in depth_data:
                depth_data[hyperlink] = depth + 1
                queue.append((hyperlink, depth + 1))
                new_addings += 1 

        print(f"We have {len(depth_data)} links extracted")
        # update json's dict
        if new_addings > 500: 
            update_jsons(depth_file_path, depth_data)
            calculate_pagerank_scores(seed_page)
            new_addings = 0


# In[191]:


def find_hyperlinks(url, seed_page, num_ban):
    
    if num_ban > 3:
        return set()
    
    driver_path = '/snap/chromium/2614/usr/lib/chromium-browser/chromedriver'
    chrome_binary_path = '/usr/bin/google-chrome'
    is_rendered = seed_page.is_rendered
    hyperlinks = set()
    G = seed_page.dir_graph
    
    if is_rendered == True:
        try:
            driver = get_driver(driver_path, chrome_binary_path)
            driver.get(url) 
            waiting_time = 10
            wait(waiting_time)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            for a in soup.find_all('a', href = True):
                rel_attribute = a.get('rel')
                if rel_attribute is None or 'nofollow' not in rel_attribute:
                    complete_link = find_complete_link(a, url)
                    if not complete_link:
                        continue            

                hyperlinks.add(complete_link)
                G.add_edge(url, complete_link)

            driver.quit()
        except WebDriverException as e:
            if "net::ERR" in str(e):
                print(f"You are banned by the site in fetching {url} please wait 1 minute :)")
                wait(60)
                return find_hyperlinks(url, seed_page, num_ban + 1)
            
        except Exception as e:
            print(f"{e}")
        
        if len(hyperlinks) == 1:
            for link in hyperlinks:
                if 'recaptch' in link:
                    print(f"You are banned by the site in fetching {url} please wait 1 minute :)")
                    wait(60)
                    return find_hyperlinks(url, seed_page, num_ban + 1)

        return hyperlinks
    
    elif is_rendered == False:
        try:
            response = requests.get(url, timeout = 30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                for a in soup.find_all('a', href = True):
                    rel_attribute = a.get('rel')
                    if rel_attribute is None or 'nofollow' not in rel_attribute:
                        complete_link = find_complete_link(a, url)
                        if not complete_link:
                            continue

                    hyperlinks.add(complete_link)
                    G.add_edge(url, complete_link)
                                    
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            
            
        if len(hyperlinks) == 1:
            for link in hyperlinks:
                if 'recaptch' in link:
                    print(f"You are banned by the site in fetching {url} please wait 1 minute :)")
                    wait(60)
                    return find_hyperlinks(url, seed_page, num_ban + 1)
            
        return hyperlinks
    
    else:
        seed_page.is_rendered, hyperlinks = download_or_render(url, num_ban)
        for link in hyperlinks:
            G.add_edge(url, link)
        return hyperlinks


# In[6]:


def breakdown_url(url):
    parsed_url = urlparse(url)
    scheme, domain = parsed_url.scheme, parsed_url.netloc
    base_url = scheme + "://" + domain
    return scheme, domain, base_url


# In[176]:


def find_complete_link(a, url):
    
    scheme, domain, base_url = breakdown_url(url)
    
    href = unquote(a['href'])
    
    excluded_extensions = ['.mp4', '.mp3', '.apk', '.png', '.pdf', '.xlsx', '.zip', '.xml', '.html']
    social_apps = ['twitter', 'instagram', 'youtube', 't.me', 'telegram', 'linkedin', 'facebook', 'javascript']
    if any(href.endswith(ext) for ext in excluded_extensions):
        return 0
    if any(social_app.lower() in href.lower() for social_app in social_apps):
        return 0

    if href[0:4].lower() == "http":
        complete_link = href
    elif href[0:2] == "//":
        complete_link = scheme + ":" + href
    else:
        complete_link = base_url + href
        
    if '#' in complete_link:
        parts = complete_link.split('#')
        complete_link = parts[0]
        
    if '?' in complete_link:
        parts = complete_link.split('?')
        complete_link = parts[0]
    
    if complete_link[-1] == '/':
        complete_link = complete_link[:-1]
    

    return remove_www(complete_link)


# In[8]:


def remove_www(url):
    if 'www' in url:
        index = url.index('www')
        return url[:index] + url[index + 4: ]
    else:
        return url


# In[9]:


def get_driver(driver_path, chrome_binary_path):
    user_agents_list = [
        {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"}, 
        {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36"}
    ]
    selected_header = random.sample(user_agents_list, 1)[0]
    # Create a ChromeService object and set the path to the Chrome binary
    chrome_service = ChromeService(driver_path, chrome_binary=chrome_binary_path)

    # Initialize a headless Chrome browser
    options = webdriver.ChromeOptions()
    options.add_argument("--enable-javascript")
    options.add_argument('--headless')  # Run in headless mode (no GUI)
    options.add_argument('--disable-gpu')  # Required for headless mode on some systems
    options.add_argument('--no-sandbox')  # Required for headless mode on some systems
    options.add_argument('--disable-dev-shm-usage')  # Required for headless mode on some systems
    options.add_argument('--disable-infobars')  # Disable infobars
    custom_user_agent = selected_header['User-Agent']    
    options.add_argument(f'user-agent={custom_user_agent}')
    
    # Pass the ChromeService instance when creating the Chrome WebDriver
    driver = webdriver.Chrome(service=chrome_service, options=options)
    driver.set_page_load_timeout(90)
    return driver


# In[43]:


def wait(seconds):
    start_time = time.time()
    wait_interval = 1
    while True:
        if time.time() - start_time > seconds:
            break
        time.sleep(wait_interval)


# In[190]:


def download_or_render(url, num_ban):
    
    if num_ban > 3:
        return set()
    
    driver_path = '/snap/chromium/2614/usr/lib/chromium-browser/chromedriver'
    chrome_binary_path = '/usr/bin/google-chrome'
    downloaded_links = set()
    rendered_links = set()
    
    try:
        response = requests.get(url, timeout = 30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for a in soup.find_all('a', href = True):
                rel_attribute = a.get('rel')
                if rel_attribute is None or 'nofollow' not in rel_attribute:
                    complete_link = find_complete_link(a, url)
                    if not complete_link:
                        continue
                    
                downloaded_links.add(complete_link)
                
    except Exception as e:
        print(f"{e}")
    
    try:
        driver = get_driver(driver_path, chrome_binary_path)
        driver.get(url) 
        waiting_time = 10
        wait(waiting_time)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        for a in soup.find_all('a', href = True):
            rel_attribute = a.get('rel')
            if rel_attribute is None or 'nofollow' not in rel_attribute:
                complete_link = find_complete_link(a, url)
                if not complete_link:
                    continue            

            rendered_links.add(complete_link)

        driver.quit() 
    except WebDriverException as e:
        if "net::ERR" in str(e):
            print(f"You are banned by the site in fetching {url} please wait 1 minute :)")
            wait(60)
            return download_or_render(url, num_ban + 1)
        
    except Exception as e:
        print(f"{e}")

    print(len(rendered_links))
    if len(downloaded_links) == len(rendered_links):
        # The page doesn't need rendering
        return False, downloaded_links
    else:
        return True, rendered_links


# In[11]:


def update_jsons(file_path, dic):
    try:
        with open(file_path, 'r') as file:
            loaded_dic = json.load(file)
        loaded_dic.update(dic)
        with open(file_path, 'w') as file:
            json.dump(loaded_dic, file, indent=None, separators=(',', ': '))
    except:
        with open(file_path, 'w') as file:
            json.dump(dic, file, indent=None, separators=(',', ': '))


# In[130]:


def calculate_pagerank_scores(seed_page):
    
    final_scores = {}
    score_file_path = urlparse(seed_page.url).netloc + "scores.json"
    G = seed_page.dir_graph
    pagerank_scores = nx.pagerank(G)
    sorted_pagerank_scores = dict(sorted(pagerank_scores.items(), key=lambda item: item[1], reverse=True))
    update_jsons(dic=sorted_pagerank_scores, file_path=score_file_path)
    return sorted_pagerank_scores


# In[192]:


url = input()
seed_page = SeedPage(url)
go_to_depth(seed_page)


# In[193]:


scores = calculate_pagerank_scores(seed_page)
for page, score in scores.items():
    print(f"{page}: {score}")

