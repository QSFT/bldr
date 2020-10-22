import subprocess
from pathlib import Path
from typing import Mapping

import pytest

from bldr.bldr import BLDR
from ..testutil import copytree, extract_deb


@pytest.fixture
def quilt_project_path(tmp_path: Path, asset_dir: Path, git_env: Mapping[str, str]) -> Path:
    quilt_project_dir = tmp_path.joinpath('quilt_project')
    quilt_project_dir.mkdir()
    subprocess.check_call(['git', 'init'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'checkout', '-b', 'upstream'], cwd=quilt_project_dir)

    copytree(asset_dir.joinpath('test-quilt-proj-onedir', 'upstream'), quilt_project_dir)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported upstream'], cwd=quilt_project_dir, env=git_env)

    subprocess.check_call(['git', 'checkout', '-b', 'ubuntu'], cwd=quilt_project_dir)
    copytree(asset_dir.joinpath('test-quilt-proj-onedir', 'debian'), quilt_project_dir)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported debian'], cwd=quilt_project_dir, env=git_env)

    subprocess.check_call(['git', 'checkout', '-b', 'master'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'reset', '--hard', 'ubuntu'], cwd=quilt_project_dir)

    return quilt_project_dir


def test_quilt_project_build(local_repo_dir: Path, quilt_project_path: Path, docker_from: str, tmp_path: Path):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=quilt_project_path.parent,
        docker_from=docker_from,
    )
    bldr.build(quilt_project_path)

    quilt_proj_deb_file = list(local_repo_dir.glob('**/quilt-proj*.deb'))[0]

    extract_dir = tmp_path.joinpath('extracted')
    extract_dir.mkdir()
    extract_deb(quilt_proj_deb_file, extract_dir)

    content = extract_dir.joinpath('usr', 'share', 'doc', 'feeling', 'alone').read_text()
    assert content == "Hello, friend!\n", "The patched file should be correct."

    content = extract_dir.joinpath('usr', 'share', 'doc', 'feeling', 'lonely').read_text()
    assert content == "I am a test.\n", "The patched file should be correct."
