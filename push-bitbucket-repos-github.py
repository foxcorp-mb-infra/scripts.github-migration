#!/usr/bin/env python3
"""
This script will push Bitbucket cloned repos from the provided directory into the
Github repository that has the same name.  It requires a bearer token in
environment variable GITHUB_TOKEN.  User running this script must have Owner
access to the GitHub Organization
"""

import argparse
import os
import threading
import sys
import logging
import time
import subprocess
import shutil

from pathlib import Path
from subprocess import DEVNULL

LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.push-repos-github'
PROCESS_TIMEOUT = 300  # default process timeout
DEFAULT_GH_URL = 'git@github.com:'

concurrency_sem = threading.Semaphore(DEFAULT_NUM_THREADS)


def main():
    """ The main entry point for the script. Required args for Github organization
        name and the local path to the cloned repositories to push
    """
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--org-name', type=str, required=True, help='Name of the Github Organization')
    parser.add_argument('--cloned-repos-path', type=Path, required=True, help='Path of the cloned repo')

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

    # start a thread per repo
    threads = []

    allrepos = os.listdir(args.cloned_repos_path)
    for repo_name in allrepos:
        if repo_name.startswith("."):
            continue
        worker = threading.Thread(
            target=process_repo,
            args=(repo_name, args.cloned_repos_path, args.org_name),
        )
        threads.append(worker)

    for worker in threads:
        worker.daemon = True  # helps to cancel cleanly
        worker.start()
    for worker in threads:
        worker.join(timeout=PROCESS_TIMEOUT)


def process_repo(repo_name, cloned_repos_path, org_name):
    """ The main work process will attempt to push to Github and retry on failure """
    logfile = os.path.abspath(os.path.join(LOGGING_DIR, repo_name))
    duration = 5
    tries = 0
    done = False
    with concurrency_sem:
        while tries <= 3:
            done = push_repo_github(repo_name, cloned_repos_path, org_name)
            if done:
                break
            tries += 1
            logging.info('%s backing off %ds try %d...', repo_name, duration, tries)
            time.sleep(duration)
            duration += (duration * 0.3)
    if not done:
        logging.error('Error processing %s, giving up.  See %s for details.', repo_name, logfile)

    return


def push_repo_github(repo_name, cloned_repos_path, org_name):
    """ Using the git command from the CLI set the remote, push to origin """
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info('pushing %s to Github organization: %s', repo_name, org_name)

    git_ref = f"{DEFAULT_GH_URL}{org_name}/{repo_name}.git"
    working_dir = os.path.join(cloned_repos_path, repo_name)

    with open(logfile, 'w', encoding='UTF-8') as log_file_handle:
        try:
            subprocess.run(
                f'git push {git_ref} +refs/remotes/origin/\*:refs/heads/\* && git push {git_ref} --tags',
                cwd=working_dir,
                shell=True,
                stdin=DEVNULL,
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=PROCESS_TIMEOUT,
            )
        except subprocess.CalledProcessError as cpe:
            logging.exception(cpe)  # log the exception but don't stop the other threads
            logging.error('Error cloning %s, see %s for details', repo_name, logfile)
            return False
        except subprocess.TimeoutExpired:
            logging.error('Timeout updating %s, see %s for details', repo_name, logfile)
            return False
    return True


if __name__ == '__main__':
    main()
