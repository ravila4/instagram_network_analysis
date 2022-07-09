from calendar import c
import collections
import json
import random
import re
import sys
import time
from collections import defaultdict
from tkinter import W

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
    times_restarted = 0  # keep track of how many times profile page has to be refreshed

    def login(self, username, password):
        self.username = username
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

    def get_my_user_id(self):
        self.go_to_page("https://instagram.com/" + self.username )
        time.sleep(2)
        user_info_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}"
        for request in self.driver.requests:
            if request.url == user_info_url:
                response = request.response
                if response.status_code == 200:
                    user_info = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
                    user_info = json.loads(user_info.decode('utf-8'))
                    user_id = user_info['data']['user']['id']
                    return user_id

    def get_my_followers(self):
        user_id = self.get_my_user_id()
        assert user_id is not None, "Could not get user id."
        self.go_to_page("https://instagram.com/" + self.username + "/followers/")
        time.sleep(4)
        my_followers_set = set()
        followers_url = f"https://i.instagram.com/api/v1/friendships/{user_id}/followers/"
        headers = None
        # The web driver cache has the cookies and headers required to make the requests.
        for request in self.driver.requests:
            if request.url.startswith(followers_url):
                if request.response.status_code == 200:
                    headers = request.headers
                    params = request.params
                    break
        assert headers is not None, "Could not find the headers to request followers."
        # Get cookies
        cookies_dict = {}
        for cookie in self.driver.get_cookies():
            cookies_dict[cookie['name']] = cookie['value']
        # Change `count` parameter to get more followers
        params['count'] = 200
        # Request followers
        response = requests.get(followers_url, headers=headers, params=params, cookies=cookies_dict)
        response.raise_for_status()
        followers = response.json()
        for follower in followers['users']:
            my_followers_set.add((follower['username'], follower['full_name'], follower['profile_pic_url']))
        next_id = followers['next_max_id']
        # Iterate over the next pages of followers
        while next_id is not None:
            params['max_id'] = next_id
            response = requests.get(followers_url, headers=headers, params=params, cookies=cookies_dict)
            response.raise_for_status()
            followers = response.json()
            for follower in followers['users']:
                my_followers_set.add((follower['username'], follower['full_name'], follower['profile_pic_url']))
            next_id = followers.get('next_max_id')
        return list(my_followers_set)

    def get_followers(self, my_followers_arr, start_profile, relations_file):
        n_my_followers = len(my_followers_arr)
        count_my_followers = start_profile - 1

        for current_profile in my_followers_arr[start_profile - 1 : -1] + [my_followers_arr[-1]]:
            print("Start scraping " + current_profile)
            self.go_to_page(current_profile)
            time.sleep(random.randint(5, 20))
            last_5_following = collections.deque([1, 2, 3, 4, 5])  # keep track of Instagram blocking scroll requests
            count_my_followers += 1

            with open('start_profile.txt', 'w+') as outfile: # keep track of last profile checked
                outfile.write(str(count_my_followers))

            followers = self.driver.find_elements("class name", "-nal3")
            followers[2].click()
            time.sleep(2)
            initialise_vars = 'elem = document.getElementsByClassName("isgrP")[0]; followers = parseInt(document.getElementsByClassName("g47SY")[1].innerText); times = parseInt(followers * 0.14); followersInView1 = document.getElementsByClassName("FPmhX").length'
            initial_scroll = 'elem.scrollTop += 500'
            next_scroll = 'elem.scrollTop += 2000'

            with open('./jquery-3.3.1.min.js', 'r') as jquery_js:
                # 3) Read the jquery from a file
                jquery = jquery_js.read()
                # 4) Load jquery lib
                self.driver.execute_script(jquery)
                # scroll down the page
                self.driver.execute_script(initialise_vars)
                # self.driver.execute_script(scroll_followers)
                self.driver.execute_script(initial_scroll)
                time.sleep(random.randint(2, 5))

                next = True
                follow_set = set()
                # check how many people this person follows
                nr_following = int(re.sub(",","",self.driver.find_elements("class name", "g47SY")[2].text))

                n_li = 1
                while next:
                    print(str(count_my_followers) + "/" + str(n_my_followers) + " " + str(n_li) + "/" + str(nr_following))
                    time.sleep(random.randint(7, 12) / 10.0)
                    self.driver.execute_script(next_scroll)
                    time.sleep(random.randint(7, 12) / 10.0)
                    if not (n_li < nr_following - 11):
                        next = False

                    n_li = len(self.driver.find_elements("class name", "FPmhX"))
                    last_5_following.appendleft(n_li)
                    last_5_following.pop()
                    # if instagram starts blocking requests, reload page and start again
                    if len(set(last_5_following)) == 1:
                        print("Instagram seems to keep on loading. Refreshing page in 7 seconds")
                        self.times_restarted += 1
                        if self.times_restarted == 4:
                            print("Instagram keeps on blocking your request. Terminating program. Start it again later.")
                            sys.exit()
                        time.sleep(7)
                        self.get_followers(my_followers_arr, count_my_followers, relations_file)

                self.times_restarted = 0

                following = self.driver.find_elements("class name", "FPmhX")
                for follow in following:
                    profile = follow.get_attribute('href')
                    if profile in my_followers_arr:
                        follow_set.add((current_profile, profile))

                with open(relations_file, "a") as outfile:
                    for relation in follow_set:
                        outfile.write(relation[0] + " " + relation[1] + "\n")

                print("This person follows " + str(len(follow_set)) + " of your connections. \n")

        sys.exit()

