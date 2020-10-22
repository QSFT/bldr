import subprocess
import shutil
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

    copytree(asset_dir.joinpath('test-quilt-proj', 'upstream'), quilt_project_dir)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported older upstream'], cwd=quilt_project_dir, env=git_env)
    subprocess.check_call(['git', 'tag', 'upstream-older'], cwd=quilt_project_dir)

    copytree(asset_dir.joinpath('test-quilt-proj', 'upstream-newer'), quilt_project_dir, exist_ok=True)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported newer upstream'], cwd=quilt_project_dir, env=git_env)
    subprocess.check_call(['git', 'tag', 'upstream-newer'], cwd=quilt_project_dir)

    subprocess.check_call(['git', 'checkout', 'upstream-older'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'checkout', '-b', 'ubuntu'], cwd=quilt_project_dir)

    copytree(asset_dir.joinpath('test-quilt-proj', 'debian'), quilt_project_dir, exist_ok=True)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported debian older version'], cwd=quilt_project_dir, env=git_env)
    subprocess.check_call(['git', 'tag', 'debian-older'], cwd=quilt_project_dir)

    subprocess.check_call(['git', 'merge', 'upstream-newer', '--no-commit'], cwd=quilt_project_dir, env=git_env)
    copytree(asset_dir.joinpath('test-quilt-proj', 'debian-newer'), quilt_project_dir, exist_ok=True)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Imported debian newer version'], cwd=quilt_project_dir, env=git_env)
    subprocess.check_call(['git', 'tag', 'debian-newer'], cwd=quilt_project_dir)

    subprocess.check_call(['git', 'checkout', '-b', 'master'], cwd=quilt_project_dir)
    copytree(asset_dir.joinpath('test-quilt-proj', 'master'), quilt_project_dir, exist_ok=True)
    subprocess.check_call(['git', 'add', '--all'], cwd=quilt_project_dir)
    subprocess.check_call(['git', 'commit', '--no-verify', '--message', 'Our patches'], cwd=quilt_project_dir, env=git_env)

    return quilt_project_dir


def do_build(local_repo_dir: Path, quilt_project_path: Path, docker_from: str, tmp_path: Path, expected_output: str) -> None:
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

    output = subprocess.check_output(['usr/bin/am-i-quilted'], cwd=extract_dir).decode('utf-8')
    assert output == expected_output, "The script output should be what expected"

    shutil.rmtree(str(extract_dir), ignore_errors=True)


def test_quilt_project_build(local_repo_dir: Path, quilt_project_path: Path, docker_from: str, tmp_path: Path):
    subprocess.check_call(['git', 'checkout', 'debian-older'], cwd=quilt_project_path)
    expected_output = (
        "So I am a little script from upstream\n"
        "A little bit buggy though.\n"
        "But do you still love me?\n"
    )
    debian_older_local_repo_dir = local_repo_dir.joinpath('debian-older')
    do_build(debian_older_local_repo_dir, quilt_project_path, docker_from, tmp_path, expected_output)

    subprocess.check_call(['git', 'checkout', 'debian-newer'], cwd=quilt_project_path)
    expected_output = (
        "So I am a newer little script from upstream\n"
        "A little bit buggy though.\n"
        "But do you still love me?\n"
    )
    debian_newer_local_repo_dir = local_repo_dir.joinpath('debian-newer')
    do_build(debian_newer_local_repo_dir, quilt_project_path, docker_from, tmp_path, expected_output)

    subprocess.check_call(['git', 'checkout', 'master'], cwd=quilt_project_path)
    expected_output = (
        "So I am a newer little script from upstream\n"
        "A little bit buggy though.\n"
        "But do you still really love me?\n"
    )
    master_local_repo_dir = local_repo_dir.joinpath('master')
    do_build(master_local_repo_dir, quilt_project_path, docker_from, tmp_path, expected_output)

    debian_newer_dsc = debian_newer_local_repo_dir.joinpath('quilt_project', 'debs', 'quilt-proj_1.1-1ubuntu1.dsc')
    master_dsc = master_local_repo_dir.joinpath('quilt_project', 'debs', 'quilt-proj_1.1-1ubuntu1bb50.1.dsc')

    assert 'quilt-proj_1.1.orig.tar.gz' in debian_newer_dsc.read_text(), "The script should generate the same orig.tar.gz every time."
    assert 'quilt-proj_1.1.orig.tar.gz' in master_dsc.read_text(), "The script should generate the same orig.tar.gz every time."
