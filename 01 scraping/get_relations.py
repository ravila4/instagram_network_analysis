import argparse
import os.path

from bot import InstagramBot


def generate_txt(relations_file, my_followers_arr, username):
    relations = open(relations_file, 'w+')
    user_url = "https://instagram.com/" + username + "/"
    for follower in my_followers_arr:
        follower_url = "https://instagram.com/" + follower.split(',')[0] + "/"
        relations.write(follower_url + " " + user_url + "\n")
        relations.write(user_url + " " + follower_url + "\n")


def get_start_profile():
    with open('start_profile.txt') as f:
        return int(f.readline())


def get_my_followers_from_txt():
    my_followers_arr = []
    with open('my_followers.txt') as f:
        for line in f:
            my_followers_arr.append(line.rstrip('\n'))
    return my_followers_arr


def get_relations(config):
    relations_file = config.relations_file
    username = config.username
    password = config.password
    ig = InstagramBot()

    ig.start()
    ig.login(username, password)

    my_followers_arr = get_my_followers_from_txt()
    if not os.path.isfile(relations_file):
        generate_txt(relations_file, my_followers_arr, username)

    if os.path.isfile('start_profile.txt'):
        start_profile = get_start_profile()
        print("Start scraping at profile nr " + str(start_profile))
    else:
        start_profile = 1
        with open('start_profile.txt', 'w+') as outfile:
            outfile.write("1")

    ig.get_followers_following(my_followers_arr, start_profile, relations_file)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    # input parameters
    parser.add_argument('--relations_file', type=str)
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)

    config = parser.parse_args()

    get_relations(config)
