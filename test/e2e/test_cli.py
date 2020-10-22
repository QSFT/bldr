from pathlib import Path

from pytest_console_scripts import ScriptRunner

from bldr.version import get_version
from ..testutil import skip_if_global_config


def test_version(script_runner: ScriptRunner):
    ret = script_runner.run('bldr', '--version')
    assert ret.success, "version print should be succeded"
    assert ret.stdout == 'bldr {}\n'.format(get_version())
    assert ret.stderr == '', "nothing should be written to stderr"


@skip_if_global_config
def test_selftest(script_runner: ScriptRunner):
    ret = script_runner.run('bldr', 'selftest')
    assert ret.success, "selftest command should be succeded"
    assert ret.stderr == '', "nothing should be written to stderr"


@skip_if_global_config
def test_build(script_runner: ScriptRunner, asset_dir: Path, docker_from: str, local_repo_dir: Path):
    ret = script_runner.run('bldr', 'build', docker_from, "--local-repo-dir", str(local_repo_dir), cwd=asset_dir.joinpath('example-lang-C'))
    assert ret.success, "build command should be succeded"
    assert 'Your deb files are at' in ret.stdout
    assert ret.stderr == '', "nothing should be written to stderr"

    assert local_repo_dir.joinpath("Packages").is_file(), "Packages file should exist"
    assert local_repo_dir.joinpath("Sources").is_file(), "Packages file should exist"
    assert local_repo_dir.joinpath("Packages").stat().st_size > 0, "Packages file should be non-empty"
    assert local_repo_dir.joinpath("Sources").stat().st_size > 0, "Sources file should be non-empty"


@skip_if_global_config
def test_failed_build(script_runner: ScriptRunner, asset_dir: Path, docker_from: str, local_repo_dir: Path):
    ret = script_runner.run('bldr', 'build', docker_from, "--local-repo-dir", str(local_repo_dir), cwd=asset_dir.joinpath('never-builds'))
    assert not ret.success, "build command should be failed"
    assert ret.stderr == '', "nothing should be written to stderr"

    assert local_repo_dir.joinpath("Packages").is_file(), "Packages file should exist"
    assert local_repo_dir.joinpath("Sources").is_file(), "Sources file should exist"
    assert local_repo_dir.joinpath("Packages").stat().st_size == 0, "Packages file should be empty"
    assert local_repo_dir.joinpath("Sources").stat().st_size == 0, "Sources file should be empty"


@skip_if_global_config
def test_reindex(script_runner: ScriptRunner, asset_dir: Path, reindex_data: Path, tmp_path: Path, docker_from: str):
    ret = script_runner.run('bldr', 'reindex', docker_from, '--local-repo-dir', reindex_data)
    assert ret.success, "reindex command should be succeded"
    assert ret.stderr == '', "nothing should be written to stderr"

    expected_packages_content = asset_dir.joinpath('test-reindex-data', 'Packages.correct').read_text()
    assert reindex_data.joinpath('Packages').read_text() == expected_packages_content, 'Generated Packages file should be identical to Packages.correct'

    expected_sources_content = asset_dir.joinpath('test-reindex-data', 'Sources.correct').read_text()
    assert reindex_data.joinpath('Sources').read_text() == expected_sources_content, 'Generated Sources file should be identical to Sources.correct'


def test_command_names_in_help(script_runner: ScriptRunner):
    ret = script_runner.run('bldr', '--help')
    assert ret.success
    for command_name in ['build', 'shell', 'reindex', 'selftest']:
        assert command_name in ret.stdout


def test_command_help(script_runner: ScriptRunner):
    ret = script_runner.run('bldr', 'build', '--help')
    assert ret.success

    argument_list = [
        'docker_from',
        'package',
        '--snapshot',
        '--shell',
        '--deb-build-options',
        '--local-repo-dir',
        '--nocache',
        '--container-env',
        '--hooks-dir',
    ]
    for argument in argument_list:
        assert argument in ret.stdout


def test_config_with_a_non_existent_file(script_runner: ScriptRunner, tmp_path: Path):
    config = tmp_path.joinpath('non-existent-config.json')
    ret = script_runner.run(
        'bldr', '--config', str(config), 'build', 'ubuntu:bionic'
    )
    assert not ret.success
    assert "Unable to open configuration file: '{}'".format(config) in ret.stderr


def test_config_with_a_unreadable_file(script_runner: ScriptRunner, tmp_path: Path):
    config = tmp_path.joinpath('non-existent-config.json')
    config.touch()
    config.chmod(0)
    ret = script_runner.run(
        'bldr', '--config', str(config), 'build', 'ubuntu:bionic'
    )
    assert not ret.success
    assert "Unable to open configuration file: '{}'".format(config) in ret.stderr


def test_config_with_a_non_json_file(script_runner: ScriptRunner, tmp_path: Path):
    config = tmp_path.joinpath('non-existent-config.json')
    config.write_text('{"foo": ')

    ret = script_runner.run(
        'bldr', '--config', str(config), 'build', 'ubuntu:bionic'
    )
    assert not ret.success
    assert "Unable to parse configuration file: 'Expecting value: line 1 column 9 (char 8)'" in ret.stderr
