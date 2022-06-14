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


def main():
    bb_url = 'https://foxrepo.praecipio.com'
    bb_project_key = sys.argv[1]
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

    output = json.loads(response.text)
    print(f'Getting the list of repos in {bb_project_key} project, limit is {output["limit"]}')
    print(f'Number of repos found in {bb_project_key} project are {output["size"]}')
    print("Writing the repos to file bitbucket_repos.txt")
    
    with open("bitbucket_repos.txt",'w') as repos:
        for i in output["values"]:
            repos.write(f'{i["name"]}\n')

if __name__ == '__main__':
    main()