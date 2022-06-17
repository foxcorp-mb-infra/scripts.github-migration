#!/usr/bin/env python3
"""
This script deletes GH repos in the gitHub organization mentioned in the argument.
It will clean all the repos in the mirrored-repos-path directory
It requires a bearer token in environment variable GITHUB_TOKEN.
User running this script be have Owner access to the GitHub Organization.
"""

import argparse
import os
import sys
import logging
import shutil

import requests

LOG_LEVEL = logging.INFO
LOGGING_DIR = '.delete-repos-github'


def main():
    """ CLI entrypoint for clean-github-repos """
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser()
    parser.add_argument('--org-name', help='Name of the Github Organization')
    parser.add_argument('--mirrored-repos-path', help='Path of the mirrored repo')

    args = parser.parse_args()

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

    os.chdir(args.mirrored_repos_path)

    allrepos = os.listdir(args.mirrored_repos_path)
    for repo in allrepos:
        if repo.startswith("."):
            continue
        repo_name = repo[:-4]
        delete_github_repository(repo_name, github_token, args.org_name)


def delete_github_repository(repo_name, github_token, org_name):
    """ Using the Github API delete the repository from the organization """

    url = f'https://api.github.com/repos/{org_name}/{repo_name}'
    headers_json = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {github_token}"}
    response = requests.delete(url, headers=headers_json)

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
