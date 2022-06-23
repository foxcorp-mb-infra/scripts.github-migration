#!/usr/bin/env python3
"""
Checks repos in the cloned-repo-path for large objects
"""

import argparse
import concurrent.futures
import logging
import math
import os
import subprocess
import sys

BASE = 1024  # 1024 = MB, 1000 = MiB
UNITS = ['B', 'kB', 'MB', 'GB', 'TB']  # change this to reflect BASE
GH_OBJ_SIZE_LIMIT = 100 * BASE * BASE  # GitHub object size limit

LOG_LEVEL = logging.INFO


def process_repo(repo_dir):
    output = []

    # get list of objects in the repo
    # https://stackoverflow.com/questions/10622179/how-to-find-identify-large-commits-in-git-history
    # git rev-list --objects --all | git cat-file --batch-check='stuff'
    p_revlist = subprocess.Popen(['git', 'rev-list', '--objects', '--all'],
                                 cwd=repo_dir,
                                 stdout=subprocess.PIPE,
                                 bufsize=1,  # enable line buffering
                                 text=True  # stdout in text mode
                                 )
    p_catfile = subprocess.Popen(['git', 'cat-file', '--batch-check=%(objecttype) %(objectname) %(objectsize) %(rest)'],
                                 cwd=repo_dir,
                                 stdin=p_revlist.stdout,  # pipe p_revlist stdout to stdin
                                 stdout=subprocess.PIPE,
                                 bufsize=1,  # enable line buffering
                                 text=True  # stdout in text mode
                                 )
    p_revlist.stdout.close()  # allow p_revlist to get a SIGPIPE if p_catfile ends prematurely

    # parse each line and check it
    for line in p_catfile.stdout:
        # obj_rest optional because some lines only have 3 fields
        (obj_type, obj_commit, obj_size, *obj_rest) = line.rstrip().split(' ', 3)

        # we only pay attention to blobs
        if obj_type != 'blob':
            continue

        # record any objects that are at or bigger than our limit
        if (obj_size := int(obj_size)) >= GH_OBJ_SIZE_LIMIT:
            output.append({
                'obj_type': obj_type,
                'obj_commit': obj_commit,
                'obj_size': obj_size,
                'obj_rest': obj_rest[0]
            })

    # clean up the processes
    p_revlist.wait()
    p_catfile.wait()

    return output


def humanize_filesize(size):
    """
    Return a human readable string from a file size e.g. 100.1MB
    """
    base_log = int(math.log(size, BASE))
    unit = UNITS[base_log]

    return f'{size/BASE**base_log:.1f}{unit}'


def main():
    logging.basicConfig(level=LOG_LEVEL)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloned-repos-path', help='Path of the cloned repo', required=True)

    args = parser.parse_args()

    # sanity checking
    repos_path = os.path.abspath(os.path.expanduser(args.cloned_repos_path))
    if not os.path.isdir(repos_path):
        logging.critical(f'Could not find directory {repos_path}')
        sys.exit(-1)

    repo_names = os.listdir(repos_path)

    # process each repo
    futures = {}
    with concurrent.futures.ProcessPoolExecutor() as pool:
        for repo_name in repo_names:
            repo_dir = os.path.join(repos_path, repo_name)
            futures[pool.submit(process_repo, repo_dir)] = repo_name

    # collect results
    results = {}
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if len(result):
            results[futures[future]] = result

    # output sorted list of repos and large objects
    if results:
        for repo_name in sorted(results):
            print(f'{repo_name}:')
            for result in results[repo_name]:
                print(f'''{result['obj_commit']}\t{humanize_filesize(result['obj_size'])}\t{result['obj_rest']}''')
            print()
    else:
        print('No large objects found!')


if __name__ == '__main__':
    main()
