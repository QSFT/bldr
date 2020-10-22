import pytest
import re
from pathlib import Path
from typing import List

from bldr.bldr import BLDR, BLDRError


def get_local_deb_files(local_repo_dir: Path, package_prefix: str = '') -> List[str]:
    deb_file_paths = list(local_repo_dir.glob('**/{}*.deb'.format(package_prefix)))
    assert deb_file_paths, "Built debian package should be in the local repo directory"
    return [str(Path('/local-apt').joinpath(deb_file_path.relative_to(local_repo_dir))) for deb_file_path in deb_file_paths]


def test_debian_build_lang_c(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
    )
    image = bldr.build(asset_dir.joinpath('example-lang-C'))

    local_deb_files = get_local_deb_files(local_repo_dir, package_prefix='dummy_1.0-1_amd64')
    assert len(local_deb_files) == 1, "one debian package should match to the glob pattern"

    with bldr._create_container(image) as container:
        output = container.exec_run(
            command=['dpkg', '--contents', local_deb_files[0]]
        )
        deb_content = '\n'.join(sorted([line.split()[5] for line in output.strip().split('\n')]))
        expected_content = asset_dir.joinpath('expected.example-lang-c.contents').read_text()
        assert deb_content == expected_content, "Deb file should contain the expected files"

        output = container.exec_run(
            command=['dpkg', '--field', local_deb_files[0]]
        )
        assert 'Package: dummy' in output, "package name should be in the debian fields"
        assert "Version: 1.0-1" in output, "version field should be in the debian fields in the given format"
        assert 'Maintainer: Test Maintainer <test.maintainer@example.com>' in output, "maintaner should be in the debian fields"


def test_snapshot_version(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
        snapshot=True,
    )
    image = bldr.build(asset_dir.joinpath('example-lang-C'))

    with bldr._create_container(image) as container:
        local_deb_files = get_local_deb_files(local_repo_dir, package_prefix='dummy_1.0-1+xsnapshot')
        assert len(local_deb_files) == 1, "one debian package should match to the glob pattern"

        output = container.exec_run(
            command=['dpkg', '--contents', local_deb_files[0]]
        )
        deb_content = '\n'.join(sorted([line.split()[5] for line in output.strip().split('\n')]))
        expected_content = asset_dir.joinpath('expected.example-lang-c.contents').read_text()
        assert deb_content == expected_content, "Deb file should contain the expected files"

        output = container.exec_run(
            command=['dpkg', '--field', local_deb_files[0]]
        )
        assert 'Package: dummy' in output, "package name should be in the debian fields"
        assert re.search(r"^Version: 1\.0-1\+xsnapshot\+\d{4}(?:\.\d{2}){5}\+1$", output, flags=re.MULTILINE), "version field should be in the debian fields in the given format"
        assert 'Maintainer: Test Maintainer <test.maintainer@example.com>' in output, "maintaner should be in the debian fields"


def test_depencies_are_satisfied_using_local_apt(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
    )
    bldr.build(asset_dir.joinpath('libdependable'))
    image = bldr.build(asset_dir.joinpath('depend-test'))

    with bldr._create_container(image) as container:
        local_deb_files = get_local_deb_files(local_repo_dir)
        container.exec_run(['sudo', 'dpkg', '-i'] + local_deb_files)
        output = container.exec_run(['run-depend-test'])
        assert re.search(r"^I am", output, flags=re.MULTILINE), "run-depend-test output should contain the given string"


def test_symlinks(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
    )
    bldr.build(asset_dir.joinpath('symlinks'))


def test_build_fails(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
    )
    with pytest.raises(BLDRError):
        bldr.build(asset_dir.joinpath('never-builds'))
        pytest.fail("SBS should raise exception, when an error occurs during build.")


def test_debian_build_with_hooks(local_repo_dir: Path, asset_dir: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=local_repo_dir,
        source_dir=asset_dir,
        docker_from=docker_from,
        hooks_dir=asset_dir.joinpath('test-hooks')
    )
    bldr.build(asset_dir.joinpath('example-lang-C'))

    assert local_repo_dir.joinpath('pre-build.called').exists(), "pre-build hook should be called"
    assert local_repo_dir.joinpath('pre-init.called').exists(), "pre-init hook should be called"
    assert local_repo_dir.joinpath('pre-install-deps.called').exists(), "pre-install-deps hook should be called"
    assert local_repo_dir.joinpath('post-install-deps.called').exists(), "post-install-deps hook should be called"
