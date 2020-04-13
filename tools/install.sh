#!/bin/sh

which python3 || {
    echo "Python3 is missing. rcc cannot be installed"
    exit 1
}

cd
mkdir -p sandbox/rcc || {
    echo "Cannot create a sandbox location where rcc will be installed"
    exit 1
}

echo "Creating a python virtualenv to install rcc without dirtying your system python install"
cd sandbox/rcc
python3 -m venv venv || {
    echo "Cannot create a virtualenv"
    exit 1
}

venv/bin/pip3 install rcc || {
    echo "rcc failed to install. You might be missing a C compiler to install hiredis"
    echo "Install XCode, XCode developer tools, clang or gcc"
    exit 1
}

venv/bin/rcc
echo
venv/bin/rcc --version

cat <<EOF

rcc is now installed in $PWD/venv/bin/rcc

You can alias it with
alias rcc='$PWD/venv/bin/rcc'

or update your PATH
export PATH=$PWD/venv/bin:\$PATH
EOF
