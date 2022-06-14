"""
This script mirror (i.e. (clone repo with entire history) all of the Bitbucket repos mentioned in the given text file 
and mirror them in the destination directory.

It requires a bearer token in environment variable BB_TOKEN.
"""

import argparse
import os
import sys
import logging
import threading
import subprocess
import time

LOG_LEVEL = logging.INFO
DEFAULT_NUM_THREADS = 4
LOGGING_DIR = '.mirror-project'
PROCESS_TIMEOUT = 300  # default process timeout

concurrency_sem = threading.Semaphore(DEFAULT_NUM_THREADS)
if sys.platform.startswith('win32'):
    DEV_NULL = open('nul', 'r')
else:
    DEV_NULL = open('/dev/null', 'r')


def main():
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--repo_list', help='Path of the text file withBB repos to be migrated to GH')
    parser.add_argument(
        '--dest', help='Destination directory to mirror repos')
    parser.add_argument(
        '--clone_prefix', help='clone prefix url for the BB project')

    args = parser.parse_args()

    # check if BB_TOKEN is set as environment variable
    bb_token = os.getenv('BB_TOKEN')
    if bb_token is None:
        logging.error('BB_TOKEN environment variable not found')
        sys.exit(-1)

    os.chdir(args.dest)

    if not os.path.isdir(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

# start a thread per repo
    threads = []
    with open(args.repo_list) as file:
        while (repo := file.readline().rstrip()):
            threads.append(threading.Thread(
                target=process_repo, args=(repo, args.clone_prefix,)))

        for t in threads:
            t.daemon = True  # helps to cancel cleanly
            t.start()
        for t in threads:
            t.join(timeout=120)


def process_repo(repo_name, clone_prefix):
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
                done = mirror_repo(repo_name, clone_prefix)
            if done:
                break
            # backoff and try again
            tries += 1
            logging.info(f'{repo_name} backing off {duration}s try {tries}...')
            time.sleep(duration)
            duration += (duration * 0.3)
    if not done:
        msg = f"Error processing {repo_name}, giving up.  See {logfile} for details."
        logging.error(msg)
    return


def update_repo(repo_name):
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info(f'Updating {repo_name}')
    with open(logfile, 'w') as f:
        try:
            subprocess.run('git remote update',
                           cwd=repo_name,
                           shell=True,
                           stdin=DEV_NULL,
                           stdout=f,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError:
            msg = f"Error updating {repo_name}, see {logfile} for details"
            logging.error(msg)
            return False
        except subprocess.TimeoutExpired:
            msg = f"Timeout updating {repo_name}, see {logfile} for details"
            logging.error(msg)
            return False
    return True


def mirror_repo(repo_name, clone_prefix):
    logfile = os.path.join(LOGGING_DIR, repo_name)
    logging.info(f'Cloning {repo_name}')
    with open(logfile, 'w') as f:
        try:
            subprocess.run(f'git clone --mirror {clone_prefix}/{repo_name}.git',
                           shell=True,
                           stdin=DEV_NULL,
                           stdout=f,
                           stderr=subprocess.STDOUT,
                           check=True,
                           timeout=PROCESS_TIMEOUT)
        except subprocess.CalledProcessError:
            msg = f"Error cloning {repo_name}, see {logfile} for details"
            logging.error(msg)
            return False
        except subprocess.TimeoutExpired:
            msg = f"Timeout updating {repo_name}, see {logfile} for details"
            logging.error(msg)
            return False
    return True


if __name__ == '__main__':
    main()
