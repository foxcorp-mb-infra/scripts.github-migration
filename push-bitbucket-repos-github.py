"""
This script will push Bitbucket mirrored repos from source folder to github
It requires a bearer token in environment variable GITHUB_TOKEN.
"""

import argparse
import os
import threading
import sys
import logging
import time
import subprocess
import shutil
from subprocess import DEVNULL


LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.push-repos-github'
PROCESS_TIMEOUT = 300  # default process timeout
DEFAULT_GH_URL = 'git@github.com:'

concurrency_sem = threading.Semaphore(DEFAULT_NUM_THREADS)


def main():
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--org-name', help='Name of the Github Organization')
    parser.add_argument(
        '--mirrored-repos-path', help='Path of the mirrored repo')

    args = parser.parse_args()

    # check if GITHUB_TOKEN is set as environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token is None:
        logging.error('GITHUB_TOKEN environment variable not found')
        sys.exit(-1)

    os.chdir(args.mirrored_repos_path)

    # recreate logging dir for every run
    if os.path.isdir(LOGGING_DIR):
        shutil.rmtree(LOGGING_DIR)

    if not os.path.isdir(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

    # start a thread per repo
    threads = []

    allrepos = os.listdir(args.mirrored_repos_path)
    for repo in allrepos:
        if not repo.startswith("."):
            threads.append(threading.Thread(target=process_repo, args=(
                repo, args.mirrored_repos_path, args.org_name)))

    for t in threads:
        t.daemon = True  # helps to cancel cleanly
        t.start()
    for t in threads:
        t.join(timeout=PROCESS_TIMEOUT)


def process_repo(repo, mirrored_repos_path, org_name):
    repo_name = repo[:-4]
    logfile = os.path.join(LOGGING_DIR, repo_name)
    duration = 5
    tries = 0
    done = False
    with concurrency_sem:
        while tries <= 3:
            done = push_repo_github(repo, mirrored_repos_path, org_name)
            if done:
                break
            tries += 1
            logging.info(
                '%s backing off %ds try %d...', repo_name, duration, tries)
            time.sleep(duration)
            duration += (duration * 0.3)
    if not done:
        logging.error(
            'Error processing %s, giving up.  See %s for details.', repo_name, logfile)

    return


def push_repo_github(repo, mirrored_repos_path, org_name):
    repo_name = repo[:-4]
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info(
        'pushing %s to Github organization: %s', repo_name, org_name)

    with open(logfile, 'w') as f:
        try:
            subprocess.run(os.system(f'cd {os.path.join(mirrored_repos_path,repo)} && git remote set-url --push origin {DEFAULT_GH_URL}/{org_name}/{repo} && git push --mirror'),
                           shell=True,
                           stdin=DEVNULL,
                           stdout=f,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError:
            logging.error(
                'Error cloning %s, see %s for details', repo_name, logfile)
            return False
        except subprocess.TimeoutExpired:
            logging.error(
                'Timeout updating {repo_name}, see {logfile} for details', repo_name, logfile)
            return False
    return True


if __name__ == '__main__':
    main()
