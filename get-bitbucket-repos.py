"""
This script will get the list of repos in BitBucket Project.

Set you Bitbucket PAT as environment variable BB_TOKEN.

Pass the Bitbucket Project name as argument to the script.
"""
import requests
import json
import sys
import os
import logging
import argparse


def main():
    """Write the SSH Clone URL's for the repos found in the Project."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--project_key', help='Bitbucket Project Key')
    args = parser.parse_args()
    bb_project_key = args.project_key

    bb_url = 'https://foxrepo.praecipio.com'
    bb_token = os.getenv('BB_TOKEN')
    print(f"Bit bucket project key provided is '{bb_project_key}'")

    if bb_token is None:
        logging.error('BB_TOKEN environment variable not found')
        sys.exit(-1)

    repo_list_url = f'{bb_url}/rest/api/1.0/projects/{bb_project_key}/repos?limit=1000'

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {bb_token}"
    }

    response = requests.get(repo_list_url, headers=headers)

    if response.status_code != 200:
        raise SystemError('Get Request for repos failed..')

    repo_urls = []
    repos_json = json.loads(response.text)
    for repo in repos_json.get('values', []):
        for clone in repo['links']['clone']:
            if clone['name'] == 'ssh':
                url = clone['href']
                repo_urls.append(url)

    print(f'Getting the list of repos, limit {repos_json["limit"]}')
    print(f'Repos found in {bb_project_key} {repos_json["size"]}')
    print("Writing the ssh clone URL's to file bitbucket_repos.txt")

    with open("bitbucket_repos.txt", 'w') as repo_ssh_clone_urls:
        for url in repo_urls:
            repo_ssh_clone_urls.write("%s\n" % url)


if __name__ == '__main__':
    main()
