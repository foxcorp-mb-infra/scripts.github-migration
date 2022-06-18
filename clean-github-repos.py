#!/usr/bin/env python3
"""
This script deletes repositories from the Github organization provided. It will 
delete the repositories based on those that are currently cloned in the 
mirrored-repos-path directory.  It requires a bearer token in environment 
variable GITHUB_TOKEN. User running this script be have Owner access to the 
Github Organization.
"""

import argparse
import os
import sys
import logging
import shutil
import urllib.parse

import requests
from requests.adapters import HTTPAdapter, Retry

LOG_LEVEL = logging.INFO
LOGGING_DIR = '.delete-repos-github'
GITHUB_API_URL = 'https://api.github.com/repos'


def main():
    """ CLI entrypoint for clean-github-repos """
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--org-name', help='Name of the Github Organization')
    parser.add_argument('--mirrored-repos-path', help='Path of the mirrored repo')

    args = parser.parse_args()

    if not args.org_name or not args.mirrored_repos_path:
        logging.critical("missing required arguments")
        parser.print_help()
        sys.exit()

    # recreate logging dir for every run
    if os.path.isdir(LOGGING_DIR):
        shutil.rmtree(LOGGING_DIR)

    if not os.path.isdir(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

    # check if GITHUB_TOKEN is set as environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token is None:
        logging.error('GITHUB_TOKEN environment variable not found')
        sys.exit(-1)

    mirrored_repos_path = os.path.abspath(os.path.expanduser(args.mirrored_repos_path))
    os.chdir(args.mirrored_repos_path)

    allrepos = os.listdir(mirrored_repos_path)
    for repo_name in allrepos:
        if repo_name.startswith("."):
            continue
        delete_github_repository(repo_name, github_token, args.org_name)


def delete_github_repository(repo_name, github_token, org_name):
    """ Using the Github API delete the repository from the organization """

    url = f'{GITHUB_API_URL}/{org_name}/{repo_name}'
    headers_json = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {github_token}"}

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.25, status_forcelist=[500, 502, 503, 504])
    prefix = f"{urllib.parse.urlsplit(url).scheme}://"

    session.mount(prefix, HTTPAdapter(max_retries=retries))
    response = session.delete(url, headers=headers_json)

    if response.status_code != 204:
        logging.error(
            'Failed to delete repository %s . status_code: %d . response_text: %s',
            repo_name,
            response.status_code,
            response.text,
        )
        raise SystemExit()
    else:
        logging.info('Repository %s deleted successfully', repo_name)


if __name__ == '__main__':
    main()
