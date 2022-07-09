import collections
import json
import random
import re
import sys
import time

import requests
from selenium.common.exceptions import NoSuchElementException
from seleniumwire import webdriver
from seleniumwire.utils import decode


class Bot:
    def start(self):
        """Start web driver"""
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("--lang=en")
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.driver.implicitly_wait(20)

    def tear_down(self):
        """Stop web driver"""
        self.driver.quit()

    def go_to_page(self, url):
        try:
            self.driver.get(url)
        except NoSuchElementException as ex:
            self.fail(ex.msg)


class InstagramBot(Bot):

    headers = None
    cookies = None

    def login(self, username, password):
        self.go_to_page("https://www.instagram.com/accounts/login/")
        time.sleep(2)
        self.driver.find_element("xpath", "//input[@name='username']").send_keys(username)
        self.driver.find_element("xpath", "//input[@name='password']").send_keys(password)
        time.sleep(2)
        self.driver.find_element("xpath", "//button[contains(.,'Log In')]").click()
        time.sleep(2)
        # Not strictly necessary, but let's close the dialogs that pop up.
        # Comment out the next lines if it causes problems.
        self.driver.find_element("xpath", "//button[contains(.,'Not Now')]").click()
        time.sleep(3)
        self.driver.find_element("xpath", "//button[contains(.,'Not Now')]").click()
        time.sleep(3)

    def get_user_id(self, username):
        self.go_to_page("https://instagram.com/" + username)
        time.sleep(2)
        user_info_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        for request in self.driver.requests:
            if request.url == user_info_url:
                response = request.response
                if response.status_code == 200:
                    user_info = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
                    user_info = json.loads(user_info.decode('utf-8'))
                    user_id = user_info['data']['user']['id']
                    return user_id


    def get_followers(self, username):
        """"Get the followers of a user."""
        user_id = self.get_user_id(username)
        followers_set = set()
        followers_url = f"https://i.instagram.com/api/v1/friendships/{user_id}/followers/"
        if not self.headers:
            # get headers required to make the requests
            self.go_to_page(f"https://instagram.com/{username}/followers/")
            time.sleep(4)
            for request in self.driver.requests:
                if request.url.startswith(followers_url):
                    if request.response.status_code == 200:
                        self.headers = request.headers
                        break
            assert self.headers is not None, f"Could not find the headers to request followers"
        if not self.cookies:
            # get cookies
            cookies_dict = {}
            for cookie in self.driver.get_cookies():
                cookies_dict[cookie['name']] = cookie['value']
            self.cookies = cookies_dict
        # Request followers
        params = {"count": 200, "search_surface": "follow_list_page"}
        response = requests.get(followers_url, headers=self.headers, params=params, cookies=self.cookies)
        response.raise_for_status()
        followers = response.json()
        if len(followers) == 0:
            return []
        keys = ['username', 'full_name', 'profile_pic_url', 'pk']
        for follower in followers['users']:
            followers_set.add(tuple(follower[key] for key in keys))
        next_id = followers.get('next_max_id')
        # Iterate over the next pages of followers
        while next_id is not None:
            params['max_id'] = next_id
            response = requests.get(followers_url, headers=self.headers, params=params, cookies=self.cookies)
            response.raise_for_status()
            followers = response.json()
            for follower in followers['users']:
                followers_set.add(tuple(follower[key] for key in keys))
            next_id = followers.get('next_max_id')
        return list(followers_set)

    def get_following(self, username):
        """"Get the users followed by a user."""
        user_id = self.get_user_id(username)
        following_set = set()
        following_url = f"https://i.instagram.com/api/v1/friendships/{user_id}/following/"
        if not self.headers:
            # get headers required to make the requests
            self.go_to_page(f"https://instagram.com/{username}/following/")
            time.sleep(4)
            for request in self.driver.requests:
                if request.url.startswith(following_url):
                    if request.response.status_code == 200:
                        self.headers = request.headers
                        break
            assert self.headers is not None, f"Could not find the headers to request followers"
        if not self.cookies:
            # get cookies
            cookies_dict = {}
            for cookie in self.driver.get_cookies():
                cookies_dict[cookie['name']] = cookie['value']
            self.cookies = cookies_dict
        # Request followers
        params = {"count": 100}
        response = requests.get(following_url, headers=self.headers, params=params, cookies=self.cookies)
        response.raise_for_status()
        following = response.json()
        if len(following['users']) == 0:
            return []
        keys = ['username', 'full_name', 'profile_pic_url', 'pk']
        for follow in following['users']:
            following_set.add(tuple(follow[key] for key in keys))
        next_id = following.get('next_max_id')
        # Iterate over the next pages of followers
        while next_id is not None:
            params['max_id'] = next_id
            response = requests.get(following_url, headers=self.headers, params=params, cookies=self.cookies)
            response.raise_for_status()
            followers = response.json()
            for follower in followers['users']:
                following_set.add(tuple(follower[key] for key in keys))
            next_id = followers.get('next_max_id')
        return list(following_set)

    def get_followers_following(self, my_followers_arr, start_profile, relations_file):
        count_my_followers = start_profile - 1

        for current_profile in my_followers_arr[start_profile - 1 : -1] + [my_followers_arr[-1]]:
            print("Start scraping " + current_profile)
            username = current_profile.split("/")[-1]
            # keep track of last profile checked
            count_my_followers += 1
            with open('start_profile.txt', 'w+') as outfile:
                outfile.write(str(count_my_followers))

            following = self.get_following(username)
            time.sleep(random.randint(5, 20))
            following_intersection = set()
            for user in following:
                if user[0] in my_followers_arr:
                    user_profile = "https://instagram.com/" + user[0] + "/"
                    following_intersection.add((current_profile, user_profile))

            with open(relations_file, "a") as outfile:
                for relation in following_intersection:
                    outfile.write(relation[0] + " " + relation[1] + "\n")

            print("This person follows " + str(len(following_intersection)) + " of your connections. \n")

        sys.exit()

