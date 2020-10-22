#!/usr/bin/env python3

from pathlib import Path

version_file_path = Path(__file__).absolute().parent.joinpath('bldr', 'VERSION')


def main():
    with version_file_path.open('r') as version_file:
        current_version = version_file.read().strip()

    version_parts = [int(part) for part in current_version.split('.')]
    version_parts[-1] += 1
    bumped_version = '.'.join([str(part) for part in version_parts])

    with version_file_path.open('w') as version_file:
        version_file.write(bumped_version + '\n')

    print(bumped_version)


if __name__ == '__main__':
    main()
