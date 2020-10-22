import shutil
import subprocess
from pathlib import Path
from typing import Mapping

import pytest

from bldr.bldr import BLDR


@pytest.fixture
def git_project_path(tmp_path: Path, asset_dir: Path, git_env: Mapping[str, str]) -> Path:
    git_project_dir = tmp_path.joinpath('git_project')
    shutil.copytree(
        asset_dir.joinpath('test-git-proj'),
        git_project_dir,
    )

    subprocess.check_call(['git', 'init'], cwd=git_project_dir)
    subprocess.check_call(['git', 'remote', 'add', 'origin', 'http://example.com/test-git-proj.git'], cwd=git_project_dir)
    subprocess.check_call(['git', 'add', '--all'], cwd=git_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Initial commit for production use'], cwd=git_project_dir, env=git_env)

    return git_project_dir


def test_git_project_debian_build(local_repo_dir: Path, git_project_path: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=git_project_path.parent,
        docker_from=docker_from,
    )
    bldr.build(git_project_path)

    dsc_file_path = local_repo_dir.joinpath('git_project', 'debs', 'git-proj_2.3-4.dsc')
    assert dsc_file_path, "Built dsc file should be in the local repo directory"

    dsc_file_content = dsc_file_path.read_text()
    assert "Vcs-Git: http://example.com/test-git-proj.git" in dsc_file_content

    commit_id = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=git_project_path).decode('utf-8')
    assert "Vcs-Git-Commit-Id: {}".format(commit_id) in dsc_file_content
