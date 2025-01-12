import os
from github import Github

token = os.getenv("GITHUB_TOKEN")
g = Github(token)

# Test authentication
user = g.get_user()
print(f"Authenticated as: {user.login}")

# Test organization access
org_name = "lahteeph"
try:
    org = g.get_organization(org_name)
    print(f"Successfully accessed organization: {org.login}")
except Exception as e:
    print(f"Error accessing organization: {str(e)}")