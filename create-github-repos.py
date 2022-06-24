#!/usr/bin/env python3
"""
This script creates empty repositories in the Github organization provided.
It requires a bearer token in environment variable GITHUB_TOKEN.
User running this script must have Owner access to the GitHub Organization
"""

import argparse
import json
import logging
import os
import shutil
import sys
import urllib.parse

from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

LOG_LEVEL = logging.INFO
LOGGING_DIR = '.create-repos-github'
GITHUB_API_URL = 'https://api.github.com/orgs'


def main():
    """ CLI entry point for create-github-repos"""
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--org-name', type=str, required=True, help='Name of the Github Organization')
    parser.add_argument(
        '--cloned-repos-path',
        type=Path,
        required=True,
        help='Directory path to the cloned repositories',
    )

    args = parser.parse_args()
    # check if GITHUB_TOKEN is set as environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token is None:
        logging.error('GITHUB_TOKEN environment variable not found')
        sys.exit(-1)

    cloned_repos_path = os.path.abspath(os.path.expanduser(args.cloned_repos_path))
    os.chdir(cloned_repos_path)

    # recreate logging dir for every run
    if os.path.isdir(LOGGING_DIR):
        shutil.rmtree(LOGGING_DIR)

    if not os.path.isdir(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

    allrepos = os.listdir(cloned_repos_path)
    for repo_name in allrepos:
        if repo_name.startswith("."):
            # skip any hidden directories like .clone-project/
            continue
        create_github_repository(repo_name, args.org_name, github_token)


def create_github_repository(repo_name, org_name, github_token):
    """ use the Github API to create a new repository in the organization """

    url = f'{GITHUB_API_URL}/{org_name}/repos'
    headers_json = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {github_token}"}

    payload = {
        "name": f"{repo_name}",
        "description": "Migrated from BB",
        "homepage": "https://github.com",
        "private": True,
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True,
    }

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.25, status_forcelist=[500, 502, 503, 504])
    prefix = f"{urllib.parse.urlsplit(url).scheme}://"

    session.mount(prefix, HTTPAdapter(max_retries=retries))
    response = session.post(url, headers=headers_json, data=json.dumps(payload))

    if response.status_code != 201:
        response_data = json.loads(response.text)
        errors = response_data.get('errors', [])
        error_message = ','.join([error["message"] for error in errors])
        logging.error(
            '%d %s: %s',
            response.status_code,
            repo_name,
            error_message,
        )
    else:
        logging.info('Repository %s created successfully', repo_name)


if __name__ == '__main__':
    main()
