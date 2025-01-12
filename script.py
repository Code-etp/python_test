import os
import requests
from github import Github


# Set up authentication
GITHUB_TOKEN = "${{secrets.TOKEN}}"
ORG_NAME = "lahteeph"
WORKFLOW_PATH = ".github/workflows/"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

def update_workflow(repo_name, file_path, content, branch="main"):
    """Update the workflow file with the new ECS action version."""
    repo = g.get_repo(f"{ORG_NAME}/{repo_name}")
    file = repo.get_contents(file_path, ref=branch)
    updated_content = content.replace(SEARCH_STRING, REPLACE_STRING)
    if SEARCH_STRING in content:
        repo.update_file(
            file_path,
            f"Update ECS task definition to {REPLACE_STRING}",
            updated_content,
            file.sha,
            branch=branch,
        )
        print(f"Updated: {repo_name}/{file_path}")
    else:
        print(f"No changes needed for: {repo_name}/{file_path}")

def main():
    """Main function to update workflows."""
    org = g.get_organization(ORG_NAME)
    for repo in org.get_repos():
        try:
            # List all files in the workflow directory
            contents = repo.get_contents(WORKFLOW_PATH)
            for content_file in contents:
                if content_file.path.endswith(".yml") or content_file.path.endswith(".yaml"):
                    # Get the content of the workflow file
                    workflow_content = content_file.decoded_content.decode("utf-8")
                    update_workflow(repo.name, content_file.path, workflow_content)
        except Exception as e:
            print(f"Error processing repo {repo.name}: {str(e)}")

if __name__ == "__main__":
    main()
