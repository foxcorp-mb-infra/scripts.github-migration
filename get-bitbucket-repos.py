#!/usr/bin/env python3
"""
This script will get the list of repos from the BitBucket Project and write the
list to a file in the current working directory. Your Bitbucket personal access
token needs to be set in the BB_TOKEN environment variable.
Pass the Bitbucket Project name as argument to the script.
"""
import argparse
import json
import logging
import os
import sys

import requests

logging.basicConfig(level=logging.INFO)

OUT_FILE_NAME = 'bitbucket_repos.txt'
BITBUCKET_URL = 'https://foxrepo.praecipio.com'


def main():
    """Write the SSH Clone URL's for the repos found in the Project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-key', type=str, required=True, help='Bitbucket Project Key')
    args = parser.parse_args()

    bb_project_key = args.project_key

    bb_token = os.getenv('BB_TOKEN')
    print(f"Bit bucket project key provided is '{bb_project_key}'")

    if bb_token is None:
        logging.error('BB_TOKEN environment variable not found')
        sys.exit(-1)

    repo_list_url = f'{BITBUCKET_URL}/rest/api/1.0/projects/{bb_project_key}/repos?limit=1000'
    headers = {"Accept": "application/json", "Authorization": f"Bearer {bb_token}"}

    logging.info("getting list from bitbucket %s", repo_list_url)
    response = requests.get(repo_list_url, headers=headers)

    response_data = json.loads(response.text)
    if response.status_code != 200:
        errors = response_data.get('errors', [])
        error_message = ','.join([error["message"] for error in errors])
        logging.critical('%d %s', response.status_code, error_message)
        sys.exit(1)

    repo_urls = []
    for repo in response_data.get('values', []):
        for clone in repo['links']['clone']:
            if clone['name'] == 'ssh':
                url = clone['href']
                repo_urls.append(url)

    print(f'Getting the list of repos, limit {response_data["limit"]}')
    print(f'Repos found in {bb_project_key} {response_data["size"]}')
    print(f"Writing the ssh clone URL's to file {OUT_FILE_NAME}")

    with open(OUT_FILE_NAME, 'w', encoding='UTF-8') as repo_ssh_clone_urls:
        repo_ssh_clone_urls.write('\n'.join(repo_urls))


if __name__ == '__main__':
    main()
