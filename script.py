import os
from github import Github, GithubException
import random
import string
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Set up authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"
WORKFLOW_PATH = ".github/workflows/"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"
CREATE_PR = False  # Set to False for direct commits

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set in the environment.")

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

def get_repositories():
    """Get list of repositories for the authenticated user."""
    try:
        user = g.get_user()
        logging.info(f"Authenticated as: {user.login}")
        
        # Get repositories where user has admin access
        repos = []
        for repo in user.get_repos():
            # Check if user has admin access to the repo
            if repo.permissions.admin:
                repos.append(repo)
        
        logging.info(f"Found {len(repos)} repositories with admin access")
        return repos
    except Exception as e:
        logging.error(f"Error getting repositories: {str(e)}")
        return []

def check_workflow_files(repo):
    """Check for workflow files in a repository."""
    try:
        # Try to get the workflows directory
        try:
            contents = repo.get_contents(WORKFLOW_PATH)
            if not isinstance(contents, list):
                contents = [contents]
        except GithubException as e:
            if e.status == 404:
                logging.info(f"No workflow directory found in {repo.name}")
                return []
            raise

        # Find all workflow files
        workflow_files = []
        for content in contents:
            if content.path.endswith(('.yml', '.yaml')):
                workflow_files.append(content)

        return workflow_files
    except Exception as e:
        logging.error(f"Error checking workflows in {repo.name}: {str(e)}")
        return []

def update_workflow_file(repo, workflow_file):
    """Update a single workflow file if it contains the search string."""
    try:
        content = workflow_file.decoded_content.decode('utf-8')
        
        if SEARCH_STRING in content:
            logging.info(f"Found match in {repo.name}/{workflow_file.path}")
            updated_content = content.replace(SEARCH_STRING, REPLACE_STRING)
            
            try:
                result = repo.update_file(
                    workflow_file.path,
                    f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}",
                    updated_content,
                    workflow_file.sha
                )
                logging.info(f"✅ Successfully updated {repo.name}/{workflow_file.path}")
                return True
            except Exception as e:
                logging.error(f"Failed to update {repo.name}/{workflow_file.path}: {str(e)}")
                return False
        else:
            logging.info(f"No match found in {repo.name}/{workflow_file.path}")
            return False
    except Exception as e:
        logging.error(f"Error processing {repo.name}/{workflow_file.path}: {str(e)}")
        return False

def main():
    """Main function to process repositories and update workflows."""
    try:
        # Get list of repositories
        repos = get_repositories()
        
        # Statistics
        total_repos = len(repos)
        repos_with_workflows = 0
        repos_updated = 0
        
        # Process each repository
        for repo in repos:
            logging.info(f"\nProcessing repository: {repo.name}")
            
            # Check for workflow files
            workflow_files = check_workflow_files(repo)
            
            if workflow_files:
                repos_with_workflows += 1
                repo_updated = False
                
                # Process each workflow file
                for workflow_file in workflow_files:
                    if update_workflow_file(repo, workflow_file):
                        repo_updated = True
                
                if repo_updated:
                    repos_updated += 1
        
        # Print summary
        logging.info("\n📊 Summary:")
        logging.info(f"Total repositories processed: {total_repos}")
        logging.info(f"Repositories with workflows: {repos_with_workflows}")
        logging.info(f"Repositories updated: {repos_updated}")
        
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
