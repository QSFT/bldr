#!/usr/bin/env python3
import argparse

from os import environ as env

from github import Github


API_TOKEN = env['GITHUB_API_TOKEN']
REPOSITORY = env['GITHUB_REPOSITORY']
BASE_BRANCH = env.get('GITHUB_BASE_BRANCH', 'master')


def create_tag(repo, name, sha):
    tag = repo.create_git_tag(name, '', sha, 'commit')
    repo.create_git_ref('refs/tags/' + tag.tag, tag.sha)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bldr_version')

    args = parser.parse_args()

    github = Github(API_TOKEN)
    repo = github.get_repo(REPOSITORY)
    head = repo.get_branch(BASE_BRANCH).commit.sha
    create_tag(repo, 'v' + args.bldr_version, head)


if __name__ == '__main__':
    main()
