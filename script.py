import os
from github import Github, GithubException
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

def get_organization_repositories():
    """Get list of repositories from both organization and user."""
    try:
        repositories = []
        
        # Try organization first
        try:
            org = g.get_organization(ORG_NAME)
            logging.info(f"Found organization: {ORG_NAME}")
            repositories.extend(list(org.get_repos()))
        except GithubException as e:
            logging.warning(f"Could not access organization {ORG_NAME}, falling back to user repos: {str(e)}")
            
        # Also get user's repositories
        user = g.get_user()
        logging.info(f"Authenticated as: {user.login}")
        user_repos = [repo for repo in user.get_repos() if repo.permissions.admin]
        
        # Combine and deduplicate repositories
        all_repos = repositories + user_repos
        unique_repos = list({repo.full_name: repo for repo in all_repos}.values())
        
        logging.info(f"Found {len(unique_repos)} total repositories")
        return unique_repos
    except Exception as e:
        logging.error(f"Error getting repositories: {str(e)}")
        return []

def get_default_branch(repo):
    """Get the default branch for a repository."""
    try:
        return repo.default_branch
    except Exception as e:
        logging.error(f"Error getting default branch for {repo.name}: {str(e)}")
        return 'main'  # fallback to main if can't determine

def has_workflow_directory(repo, branch):
    """Check if repository has a workflow directory in the specified branch."""
    try:
        try:
            repo.get_contents(WORKFLOW_PATH, ref=branch)
            return True
        except GithubException as e:
            if e.status == 404:
                return False
            raise
    except Exception as e:
        logging.error(f"Error checking workflow directory in {repo.name}: {str(e)}")
        return False

def get_workflow_files(repo, branch):
    """Get all workflow files from a repository's specified branch."""
    workflow_files = []
    try:
        contents = repo.get_contents(WORKFLOW_PATH, ref=branch)
        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            if content.type == "file" and content.path.endswith(('.yml', '.yaml')):
                workflow_files.append(content)
                logging.info(f"Found workflow file: {content.path}")

        return workflow_files
    except GithubException as e:
        if e.status == 404:
            logging.info(f"No workflow files found in {repo.name}")
        else:
            logging.error(f"Error getting workflow files in {repo.name}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error getting workflow files in {repo.name}: {str(e)}")
        return []

def update_workflow_file(repo, workflow_file, branch):
    """Update a single workflow file if it contains the search string."""
    try:
        content = workflow_file.decoded_content.decode('utf-8')
        
        if SEARCH_STRING in content:
            logging.info(f"Found match in {repo.name}/{workflow_file.path}")
            updated_content = content.replace(SEARCH_STRING, REPLACE_STRING)
            
            try:
                commit_message = f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}"
                repo.update_file(
                    workflow_file.path,
                    commit_message,
                    updated_content,
                    workflow_file.sha,
                    branch=branch
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
        repos = get_organization_repositories()
        
        # Statistics
        total_repos = len(repos)
        repos_with_workflows = 0
        repos_updated = 0
        
        # Process each repository
        for repo in repos:
            logging.info(f"\nProcessing repository: {repo.name}")
            
            # Get default branch
            default_branch = get_default_branch(repo)
            logging.info(f"Using default branch: {default_branch}")
            
            # Check if workflows directory exists in default branch
            if has_workflow_directory(repo, default_branch):
                logging.info(f"Found workflow directory in {repo.name}")
                repos_with_workflows += 1
                
                # Get workflow files from default branch
                workflow_files = get_workflow_files(repo, default_branch)
                if workflow_files:
                    logging.info(f"Found {len(workflow_files)} workflow files in {repo.name}")
                    repo_updated = False
                    
                    # Process each workflow file
                    for workflow_file in workflow_files:
                        if update_workflow_file(repo, workflow_file, default_branch):
                            repo_updated = True
                    
                    if repo_updated:
                        repos_updated += 1
            else:
                logging.info(f"No workflow directory found in {repo.name}")
        
        # Print summary
        logging.info("\n📊 Summary:")
        logging.info(f"Total repositories processed: {total_repos}")
        logging.info(f"Repositories with workflows: {repos_with_workflows}")
        logging.info(f"Repositories updated: {repos_updated}")
        
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
