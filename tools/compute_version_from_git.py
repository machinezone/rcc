import os
import sys


def computeVersion():
    try:
        gitDescribeOutPut = os.popen('git describe', 'r').read()
    except Exception:
        with open('DOCKER_VERSION') as f:
            return f.read()

    sys.stderr.write(f'git describe -> {gitDescribeOutPut}\n')

    fullVersion = gitDescribeOutPut.splitlines()[0]
    assert fullVersion[0] == 'v'

    parts = fullVersion.split('-')
    majorMinor = parts[0][1:]
    if len(parts) > 1:
        patch = parts[1]
    else:
        patch = 0

    version = f'{majorMinor}.{patch}'
    return version


if __name__ == '__main__':
    print(computeVersion())
