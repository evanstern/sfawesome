#! /bin/bash

if [ $# -lt 1 ]; then
    echo "I need the path to your .git/hooks folder as the first argument"
    echo "For example, $0 ~/checkouts/staffknex/.git/hooks"
    exit 1
fi

if [ ! -d $1 ]; then

    echo "$1 ain't no directory!"
    exit 1

fi

# OK, now let's actually do some installs...

echo "Copying commit-msg to $1..."
/bin/cp -f ./commit-msg $1/

echo "Copying parse_message to $VIRTUAL_ENV/bin/..."
/bin/cp -f parse_message $VIRTUAL_ENV/bin/

echo "Copying git-sf.py to $VIRTUAL_ENV/bin/..."
/bin/cp -f git-sf.py $VIRTUAL_ENV/bin/git-sf

echo "All done!"
