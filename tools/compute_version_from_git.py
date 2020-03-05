import os


def computeVersion():
    fullVersion = os.popen('git describe', 'r').read().splitlines()[0]
    assert fullVersion[0] == 'v'

    parts = fullVersion.split('-')
    majorMinor = parts[0][1:]
    patch = parts[1]

    version = f'{majorMinor}.{patch}'
    return version


if __name__ == '__main__':
    print(computeVersion())
