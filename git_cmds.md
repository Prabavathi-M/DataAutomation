//clone the git repo in local
git clone https://github.com/Prabavathi-M/DataAutomation.git

//navigate to main repo
cd DataAutomation/snowflake

//to see the git branches
git branch -a

//to add new branch
git branch branchname

//to switch to new branch from main
git checkout snowflake

git checkout -b snowflake origin/snowflake

git add file.sql

//tell who youare making changes to git repo
git config --global user.name "Your Name"
git config --global user.email "your_email@example.com"


git commit -m "Added file"
git push origin <branch-name>


git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.json" \
  --prune-empty --tag-name-filter cat -- --all

//to reflect latest branches in local
git fetch origin

//list remote braches
git branch -r

//to check if a file is git ignored
git check-ignore -v creds.env
git status