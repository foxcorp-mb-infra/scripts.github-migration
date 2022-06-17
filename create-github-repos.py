#!/usr/bin/env python3
"""
This script creates empty GH repos in the gitHub organization mentioned in the argument.
It requires a bearer token in environment variable GITHUB_TOKEN.
User running this script be have Owner access to the GitHub Organization
"""

import argparse
import os
import sys
import logging
import json
import shutil

import requests

LOG_LEVEL = logging.INFO
LOGGING_DIR = '.create-repos-github'


def main():
    """ CLI entry point for create-github-repos"""
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
        create_github_repository(repo_name, args.org_name, github_token)


def create_github_repository(repo_name, org_name, github_token):
    """ use the Github API to create a new repository in the organization """

    url = f'https://api.github.com/orgs/{org_name}/repos'
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

    response = requests.post(url, headers=headers_json, data=json.dumps(payload))

    if response.status_code != 201:
        logging.error(
            'Failed to create repository %s . status_code: %d . response_text: %s',
            repo_name,
            response.status_code,
            response.text,
        )
        raise SystemExit()
    else:
        logging.info('Repository %s created successfully', repo_name)


if __name__ == '__main__':
    main()
