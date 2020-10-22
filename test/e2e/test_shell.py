import getpass
import io
import os
from pathlib import Path

from pytest_console_scripts import ScriptRunner


def test_simple_commands(script_runner: ScriptRunner, docker_from: str, local_repo_dir: Path):
    stdin = io.StringIO('true\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin)
    assert ret.success, "`true` command should be succeded"
    assert ret.stderr == '', "nothing should be written to stderr"

    stdin = io.StringIO('false\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin)
    assert not ret.success, "`false` command should be failed"
    assert ret.stderr == '', "nothing should be written to stderr"

    stdin = io.StringIO('exit 255\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin)
    assert ret.returncode == 255, "exit code inside the container should be forwarded to the cli"
    assert ret.stderr == '', "nothing should be written to stderr"


def test_who_am_i_should_the_outside_user(script_runner: ScriptRunner, docker_from: str, local_repo_dir: Path):
    stdin = io.StringIO('whoami\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin)
    assert ret.success, "`whoami` command should be succeded"
    assert getpass.getuser() == ret.stdout.strip().split('\n')[-1], "outside user should be inside"
    assert ret.stderr == '', "nothing should be written to stderr"


def test_build_dependencies_should_be_installed(script_runner: ScriptRunner, asset_dir: Path, docker_from: str, local_repo_dir: Path):
    stdin = io.StringIO('dpkg -l libblkid1\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin, cwd=asset_dir.joinpath('example'))
    assert ret.success, "libblkid1 should be installed inside the shell, because it is a build dependency of e2fsprogs."
    assert ret.stderr == '', "nothing should be written to stderr"


def test_http_proxy(script_runner: ScriptRunner, docker_from: str, local_repo_dir: Path):
    env = dict(os.environ)
    env.update({'http_proxy': 'http://proxyurl.example:1234'})
    stdin = io.StringIO('env\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin, env=env)
    assert ret.success, "`env` command should be succeded"
    assert 'http_proxy=http://proxyurl.example:1234' in ret.stdout, "The shell command should pass the http_proxy env var"
    assert ret.stderr == '', "nothing should be written to stderr"

    stdin = io.StringIO('sudo env\n')
    ret = script_runner.run('bldr', 'shell', docker_from, '--local-repo-dir', local_repo_dir, stdin=stdin, env=env)
    assert ret.success, "`env` command as supersuer should be succeded"
    assert 'http_proxy=http://proxyurl.example:1234' in ret.stdout, "The env var 'http_proxy' should survive 'sudo'"
    assert ret.stderr == '', "nothing should be written to stderr"
