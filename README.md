# Bitbucket to Github migration scripts

## Requirements

These scripts are written in Python.  It is expected that Python 3.9 is installed on the system.  

- python 3.9 (https://www.python.org/downloads/)

### Python required packages

Additionally, a non-standard library is used called `requests` to allow for communication with Bitbucket and Github.com through their REST APIs.  It is expected that this package is installed and available to be used by Python.  

- requests (https://pypi.org/project/requests/)

```
$> pip install requests
```

## Expected Environment Variables

These scripts interact with Bitbucket and Github using their REST APIs.  Each requires personal access tokens to be available using the following environment variables. 

```
export BB_TOKEN=${your_bitbucket_personal_access_token}
export GITHUB_TOKEN=${your_github_personal_access_token}
```

## SSH Keys

These scripts use the `git` CLI command to clone repos from Bitbucket and push repo data to Github.com.  It is expected that appropriate ssh keys are already setup and configured to access the organization.