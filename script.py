import os
from github import Github, GithubException

# Set up authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"  # Can be personal or organizational account
WORKFLOW_PATH = ".github/workflows/"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set in the environment.")

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

def update_workflow(repo_name, file_path, content, branch="main"):
    """Update the workflow file with the new ECS action version."""
    try:
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
    except GithubException as e:
        print(f"Error updating {repo_name}/{file_path}: {e}")
    except Exception as e:
        print(f"Unexpected error updating {repo_name}/{file_path}: {e}")

def main():
    """Main function to update workflows."""
    try:
        # Determine if ORG_NAME is a user or organization
        try:
            org = g.get_organization(ORG_NAME)
            print(f"Authenticated as organization: {org.login}")
        except GithubException:
            org = g.get_user(ORG_NAME)
            print(f"Authenticated as user: {org.login}")
        
        # Process each repository
        for repo in org.get_repos():
            try:
                # List all files in the workflow directory
                contents = repo.get_contents(WORKFLOW_PATH)
                for content_file in contents:
                    if content_file.path.endswith((".yml", ".yaml")):
                        workflow_content = content_file.decoded_content.decode("utf-8")
                        update_workflow(repo.name, content_file.path, workflow_content)
            except GithubException as e:
                print(f"Error processing repo {repo.name}: {e}")
            except Exception as e:
                print(f"Unexpected error in repo {repo.name}: {e}")
    except Exception as e:
        print(f"Error accessing account: {e}")

if __name__ == "__main__":
    main()
