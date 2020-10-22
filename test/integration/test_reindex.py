from pathlib import Path

from bldr.bldr import BLDR


def test_reindex(asset_dir: Path, reindex_data: Path, tmp_path: Path, docker_from: str):
    bldr = BLDR(
        local_repo_dir=reindex_data,
        source_dir=tmp_path,
        docker_from=docker_from,
    )
    bldr.reindex()

    expected_packages_content = asset_dir.joinpath('test-reindex-data', 'Packages.correct').read_text()
    assert reindex_data.joinpath('Packages').read_text() == expected_packages_content, 'Generated Packages file should be identical to Packages.correct'

    expected_sources_content = asset_dir.joinpath('test-reindex-data', 'Sources.correct').read_text()
    assert reindex_data.joinpath('Sources').read_text() == expected_sources_content, 'Generated Sources file should be identical to Sources.correct'
