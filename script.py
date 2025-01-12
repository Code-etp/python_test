import os
from github import Github, GithubException

# Set up authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"
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
        
        # Decode content if it's base64 encoded
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # Debug print
        print(f"\nChecking file: {file_path}")
        print(f"Current content type: {type(content)}")
        print(f"Search string exists: {SEARCH_STRING in content}")
        
        if SEARCH_STRING in content:
            print(f"🔍 Found match in {repo_name}/{file_path}")
            print("Original content snippet:")
            start_idx = content.find(SEARCH_STRING)
            print(content[max(0, start_idx-50):min(len(content), start_idx+150)])
            
            updated_content = content.replace(SEARCH_STRING, REPLACE_STRING)
            
            # Verify the replacement
            if SEARCH_STRING in updated_content:
                print("⚠️ Warning: Search string still exists after replacement!")
            
            try:
                print(f"Attempting to update {repo_name}/{file_path}...")
                result = repo.update_file(
                    file_path,
                    f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}",
                    updated_content,
                    file.sha,
                    branch=branch,
                )
                print(f"Update result: {result}")
                print(f"✅ Successfully updated: {repo_name}/{file_path}")
                return True
            except GithubException as e:
                print(f"❌ Failed to update {repo_name}/{file_path}")
                print(f"Error details: {str(e)}")
                return False
        else:
            print(f"ℹ️ No match found in: {repo_name}/{file_path}")
            return False
    except GithubException as e:
        print(f"❌ Error accessing {repo_name}/{file_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error updating {repo_name}/{file_path}: {str(e)}")
        return False

def process_workflows(repo):
    """Process workflow files in a repository."""
    changes_made = False
    try:
        print(f"\nTrying to access workflow path: {WORKFLOW_PATH} in {repo.name}")
        contents = repo.get_contents(WORKFLOW_PATH)
        
        # Handle both single file and directory cases
        if not isinstance(contents, list):
            contents = [contents]
            
        print(f"Found {len(contents)} files/directories in workflows")
        
        for content_file in contents:
            print(f"\nProcessing: {content_file.path}")
            if content_file.path.endswith((".yml", ".yaml")):
                try:
                    workflow_content = content_file.decoded_content
                    if update_workflow(repo.name, content_file.path, workflow_content):
                        changes_made = True
                except Exception as e:
                    print(f"❌ Error processing {content_file.path}: {str(e)}")
                    
        return changes_made
    except GithubException as e:
        if e.status == 404:
            print(f"ℹ️ No workflows directory in repo: {repo.name}")
        else:
            print(f"❌ Error accessing workflows in repo {repo.name}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in repo {repo.name}: {str(e)}")
        return False

def main():
    """Main function to update workflows."""
    try:
        # Try to authenticate as organization first, then as user
        try:
            org = g.get_organization(ORG_NAME)
            print(f"🔑 Authenticated as organization: {org.login}")
        except GithubException:
            org = g.get_user(ORG_NAME)
            print(f"🔑 Authenticated as user: {org.login}")
        
        # Track statistics
        total_repos = 0
        updated_repos = 0
        
        # Process each repository
        for repo in org.get_repos():
            total_repos += 1
            print(f"\n📁 Processing repo: {repo.name}")
            if process_workflows(repo):
                updated_repos += 1
        
        # Print summary
        print("\n📊 Summary:")
        print(f"Total repositories processed: {total_repos}")
        print(f"Repositories updated: {updated_repos}")
        print(f"Repositories unchanged: {total_repos - updated_repos}")
        
    except Exception as e:
        print(f"❌ Error accessing account: {str(e)}")

if __name__ == "__main__":
    main()
