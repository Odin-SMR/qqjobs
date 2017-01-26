#!/bin/bash

# Run this script after cloning the base repo. Provide it with the remote path
# to your new repo.

BASE_REMOTE_URL=https://phabricator.molflow.com/diffusion/PYBASE/pybase.git

# Check that the remote still is the base repo
if [[ ! $(git config --get remote.origin.url) == $BASE_REMOTE_URL ]]; then
    echo "This is not the base repo!"
    echo $(git config --get remote.origin.url)
    echo $BASE_REMOTE_URL
    exit 1
fi

# Remove all history
rm -rf .git

# Create new repo
git init
git remote add origin "$1"

# Add everything
git add --all
git commit . -m "Initial commit"

# Push to new repo
git push origin master
