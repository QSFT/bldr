
import os
import pytest


@pytest.fixture()
def git_env():
    env = os.environ.copy()
    env["GIT_COMMITTER_NAME"] = "Test Developer"
    env["GIT_COMMITTER_EMAIL"] = "test.developer@example.com"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"]
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_NAME"]

    yield env
