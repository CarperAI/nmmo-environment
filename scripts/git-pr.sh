#!/bin/bash
MASTER_BRANCH="v1.6"

# check if in master branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" == MASTER_BRANCH ]; then
  echo "Please run 'git pr' from a topic branch."
  exit 1
fi

# check if there are any uncommitted changes
git_status=$(git status --porcelain)

if [ -n "$git_status" ]; then
  echo "You have uncommitted changes. Please commit or stash them before running 'git pr'."
  exit 1
fi

# check if there are any "xcxc" strings in the code
files=$(find . -name '*.py')
for file in $files; do
    if grep -q 'xcxc' $file; then
        echo "Found xcxc in $file!" >&2
        exit 1
    fi
done

# Run unit tests
echo "Running unit tests..."
if ! pytest; then
    echo "Unit tests failed. Exiting."
    exit 1
fi

echo "Running linter..."
if ! pylint --rcfile=pylint.cfg --fail-under=10 nmmo tests; then
    echo "Lint failed. Exiting."
    exit 1
fi

# create a new branch from current branch and reset to master
echo "Creating and switching to new topic branch..."
branch_name="git-pr-$RANDOM-$RANDOM"
git checkout -b $branch_name
git reset --soft $MASTER_BRANCH

# Verify that a commit message was added
echo "Verifying commit message..."
if ! git commit ; then
    echo "Commit message is empty. Exiting."
    exit 1
fi

# Push the topic branch to origin
echo "Pushing topic branch to origin..."
git push -u origin $branch_name

# Generate a Github pull request
echo "Generating Github pull request..."
pull_request_url="https://github.com/CarperAI/nmmo-environment/compare/$MASTER_BRANCH...CarperAI:nmmo-environment:$branch_name?expand=1"

echo "Pull request URL: $pull_request_url"


