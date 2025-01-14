from bot import InstagramBot
import argparse


def generate_my_followers_txt(my_followers):
    my_followers_txt = open("my_followers.txt", 'w+')
    for follower in my_followers:
        my_followers_txt.write(",".join([str(d) for d in follower]) + "\n")


def get_my_followers(config):
    username = config.username
    password = config.password
    ig = InstagramBot()

    ig.start()
    ig.login(username, password)
    my_followers = ig.get_followers(username)
    generate_my_followers_txt(my_followers)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    # input parameters
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)

    config = parser.parse_args()

    get_my_followers(config)
