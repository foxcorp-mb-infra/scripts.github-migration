#!/usr/bin/env python3
"""
This script mirror (i.e. clone repo with entire history) all of the Bitbucket repos mentioned in the given text file 
and mirror them in the destination directory.
It requires a bearer token in environment variable : BB_TOKEN.
"""

import argparse
import os
import sys
import logging
import threading
import subprocess
import time
import shutil
from subprocess import DEVNULL


LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.mirror-project'
PROCESS_TIMEOUT = 300  # default process timeout

concurrency_sem = threading.Semaphore(DEFAULT_NUM_THREADS)


def main():
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--repo-list', help='Path of the text file which shall contain complete ssh clone url of each BB repos to be migrated to GH, format of the file shall be one repo clone url per line')
    parser.add_argument(
        '--dest', help='Destination directory to mirror repos')

    args = parser.parse_args()

    # check if BB_TOKEN is set as environment variable
    bb_token = os.getenv('BB_TOKEN')
    if bb_token is None:
        logging.error('BB_TOKEN environment variable not found')
        sys.exit(-1)

    os.chdir(args.dest)

    # recreate logging dir for every run
    if os.path.isdir(LOGGING_DIR):
        shutil.rmtree(LOGGING_DIR)

    if not os.path.isdir(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

# start a thread per repo
    threads = []
    with open(args.repo_list) as file:
        while (repo := file.readline().rstrip()):
            threads.append(threading.Thread(
                target=process_repo, args=(repo,)))

        for t in threads:
            t.daemon = True  # helps to cancel cleanly
            t.start()
        for t in threads:
            t.join(timeout=PROCESS_TIMEOUT)


def process_repo(ssh_clone_url):
    repo_name = ssh_clone_url[6:-4].split('/')[-1]
    logfile = os.path.join(LOGGING_DIR, repo_name)
    duration = 5
    tries = 0
    done = False
    with concurrency_sem:
        while tries <= 3:
            # if the diretory exists, update the repo
            if os.path.isdir(repo_name):
                done = update_repo(repo_name)
            else:  # otherwise clone into the directory
                done = mirror_repo(ssh_clone_url, repo_name)
            if done:
                break
            # backoff and try again
            tries += 1
            logging.info('%s backing off %ds try %d',
                         repo_name, duration, tries)

            time.sleep(duration)
            duration += (duration * 0.3)
    if not done:
        logging.error(
            'Error processing %s, giving up.  See %s for details.', repo_name, logfile)
    return


def update_repo(repo_name):
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info('Updating %s', repo_name)
    with open(logfile, 'w') as f:
        try:
            subprocess.run('git remote update',
                           cwd=repo_name,
                           shell=True,
                           stdin=DEVNULL,
                           stdout=f,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError:
            logging.error(
                'Error updating %s, see %s for details', repo_name, logfile)
            return False
        except subprocess.TimeoutExpired:
            logging.error(
                'Timeout updating %s, see %s for details', repo_name, logfile)
            return False
    return True


def mirror_repo(ssh_clone_url, repo_name):
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info('Cloning %s', repo_name)
    with open(logfile, 'w') as f:
        try:
            subprocess.run(f'git clone --mirror {ssh_clone_url}',
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
                'Timeout updating %s, see %s for details', repo_name, logfile)
            return False
    return True


if __name__ == '__main__':
    main()
