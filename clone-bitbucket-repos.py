#!/usr/bin/env python3
"""
This script will clone (i.e. clone repo with entire history) all of the Bitbucket 
repos mentioned in the given text file and clone them in the destination directory.
It requires a bearer token in environment variable : BB_TOKEN.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

from pathlib import Path
from subprocess import DEVNULL

LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.clone-project'
PROCESS_TIMEOUT = 300  # default process timeout

concurrency_sem = threading.Semaphore(DEFAULT_NUM_THREADS)


def main():
    """ CLI entry point into clone-bitbucket_repos """
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--repo-list',
        type=Path,
        required=True,
        help='Path of the text file which shall contain complete ssh clone '
        'url of each Bitbucket repos to be migrated to Github, format of the '
        'file shall be one repo clone url per line',
    )
    parser.add_argument('--cloned-repos-path', type=Path, required=True, help='Destination directory to clone repos')

    args = parser.parse_args()
    working_dir = os.path.abspath(os.path.expanduser(args.cloned_repos_path))
    if not os.path.exists(working_dir):
        logging.warning("Destination directory does not exist: %s", working_dir)
        logging.info("making destination directory")
        os.makedirs(working_dir)

    if not os.path.exists(args.repo_list):
        logging.error("can't find repo list %s", args.repo_list)
        sys.exit(-1)

    # check if BB_TOKEN is set as environment variable
    bb_token = os.getenv('BB_TOKEN')
    if bb_token is None:
        logging.error('BB_TOKEN environment variable not found')
        sys.exit(-1)

    logging_dir = os.path.join(working_dir, LOGGING_DIR)
    # recreate logging dir for every run
    if os.path.isdir(logging_dir):
        shutil.rmtree(logging_dir)

    if not os.path.isdir(logging_dir):
        os.makedirs(logging_dir)

    repo_list_file_path = os.path.abspath(os.path.expanduser(args.repo_list))

    # start a thread per repo
    threads = []
    with open(repo_list_file_path, encoding="UTF-8") as repo_list_file_handle:
        for clone_url in repo_list_file_handle:
            worker = threading.Thread(target=process_repo, args=(clone_url.strip(), working_dir))
            threads.append(worker)
        for worker in threads:
            worker.daemon = True  # helps to cancel cleanly
            worker.start()
        for worker in threads:
            worker.join(timeout=PROCESS_TIMEOUT)


def process_repo(ssh_clone_url, working_dir):
    """ The main worker logic to exec the update and clone logic and retry on error """
    repo_name = convert_ssh_path_to_repo_name(ssh_clone_url)
    logfile = os.path.abspath(os.path.join(working_dir, LOGGING_DIR, repo_name))
    duration = 5
    tries = 0
    done = False
    with concurrency_sem:
        while tries <= 3:
            # if the diretory exists, update the repo
            repo_dir = os.path.join(working_dir, repo_name)
            if os.path.isdir(repo_dir):
                done = update_repo(repo_name, repo_dir, working_dir)
            else:  # otherwise clone into the directory
                done = clone_repo(ssh_clone_url, repo_name, working_dir)
            if done:
                break
            # backoff and try again
            tries += 1
            logging.info('%s backing off %ds try %d', repo_name, duration, tries)

            time.sleep(duration)
            duration += (duration * 0.3)
    if not done:
        logging.error('Error processing %s, giving up.  See %s for details.', repo_name, logfile)
    return


def update_repo(repo_name, repo_dir, working_dir):
    """ Using git from the CLI do a remote update """
    logfile = os.path.join(working_dir, LOGGING_DIR, repo_name)
    logging.info('Updating %s', repo_name)
    with open(logfile, 'w', encoding="UTF-8") as log_file_handle:
        try:
            subprocess.run(['git', 'remote', 'update'],
                           cwd=repo_dir,
                           stdin=DEVNULL,
                           stdout=log_file_handle,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError as cpe:
            logging.exception(cpe)  # log the exception but don't block other threads
            logging.error('Error updating %s, see %s for details', repo_name, logfile)
            return False
        except subprocess.TimeoutExpired:
            logging.error('Timeout updating %s, see %s for details', repo_name, logfile)
            return False
    return True


def clone_repo(ssh_clone_url, repo_name, working_dir):
    """ Using git from the CLI clone  """
    logfile = os.path.join(working_dir, LOGGING_DIR, repo_name)
    logging.info('Cloning %s', repo_name)
    with open(logfile, 'w', encoding="UTF-8") as log_file_handle:
        try:
            subprocess.run(['git', 'clone', ssh_clone_url, repo_name],
                           cwd=working_dir,
                           stdin=DEVNULL,
                           stdout=log_file_handle,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError as cpe:
            logging.exception(cpe)  # log the exception but don't block other threads
            logging.error('Error cloning %s, see %s for details', repo_name, logfile)
            return False
        except subprocess.TimeoutExpired:
            logging.error('Timeout updating %s, see %s for details', repo_name, logfile)
            return False
    return True


def convert_ssh_path_to_repo_name(ssh_path):
    """ strip off the tail `.git` and return the repository base name """
    parts = urllib.parse.urlparse(ssh_path)
    ssh_path_no_ext, _ = os.path.splitext(parts.path)
    repo_name = os.path.basename(ssh_path_no_ext)
    return repo_name


if __name__ == '__main__':
    main()
