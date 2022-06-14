"""
This script will push Bitbucket mirrored repos from source folder to github
It requires a bearer token in environment variable GITHUB_TOKEN.
"""

import argparse
import os
import threading
import sys
import logging

LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.push-repos-github'
default_github_url = 'https://github.com'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--org_name', help='Name of the Github Organization')
    parser.add_argument(
        '--mirrored_repos_path', help='Path of the mirrored repo')
    args = parser.parse_args()

    # check if GITHUB_TOKEN is set as environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token is None:
        logging.error('GITHUB_TOKEN environment variable not found')
        sys.exit(-1)

    # start a thread per repo
    threads = []

    allrepos = os.listdir(args.mirrored_repos_path)
    for repo in allrepos:
        threads.append(threading.Thread(target=push_repo_gh,
                       args=(repo, args.mirrored_repos_path, args.org_name)))

    for t in threads:
        t.daemon = True  # helps to cancel cleanly
        t.start()
    for t in threads:
        t.join(timeout=120)


def push_repo_gh(repo, mirrored_repos_path, org_name):
    os.system('cd ' + mirrored_repos_path+repo +
              ' && git remote set-url --push origin '+default_github_url+'/'+org_name+'/'+repo+'.git & & git push --mirror')


if __name__ == '__main__':
    main()
