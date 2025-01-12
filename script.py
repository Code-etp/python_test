import os
from github import Github, GithubException
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Set up authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"
CREATE_PR = False  # Set to False for direct commits

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set in the environment.")

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

def check_rate_limit():
    """Check and log the API rate limit."""
    rate_limit = g.get_rate_limit()
    remaining = rate_limit.core.remaining
    reset_time = rate_limit.core.reset
    if remaining == 0:
        sleep_time = (reset_time - time.time()) + 1
        logging.warning(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
        time.sleep(sleep_time)
    logging.info(f"API Rate Limit: {remaining}/{rate_limit.core.limit}")

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
        return 'main'

def search_and_update_files(repo, branch, path=None):
    """Recursively search and update files in all directories."""
    try:
        check_rate_limit()
        
        if path is None:
            path = ''
            
        contents = repo.get_contents(path, ref=branch)
        if not isinstance(contents, list):
            contents = [contents]
            
        updated = False
        for content in contents:
            if content.type == "dir":
                # Recursively search subdirectories
                if search_and_update_files(repo, branch, content.path):
                    updated = True
            elif content.type == "file":
                try:
                    file_content = content.decoded_content.decode('utf-8')
                    if SEARCH_STRING in file_content:
                        logging.info(f"Found match in {repo.name}/{content.path}")
                        updated_content = file_content.replace(SEARCH_STRING, REPLACE_STRING)
                        
                        commit_message = f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}"
                        repo.update_file(
                            content.path,
                            commit_message,
                            updated_content,
                            content.sha,
                            branch=branch
                        )
                        logging.info(f"✅ Successfully updated {repo.name}/{content.path}")
                        updated = True
                except Exception as e:
                    logging.error(f"Error processing file {content.path}: {str(e)}")
                    
        return updated
        
    except GithubException as e:
        if e.status == 404:
            logging.info(f"Path {path} not found in {repo.name}")
        else:
            logging.error(f"Error accessing {path} in {repo.name}: {str(e)}")
        return False

def main():
    """Main function to process repositories and update files."""
    try:
        repos = get_organization_repositories()
        
        total_repos = len(repos)
        repos_updated = 0
        
        logging.info(f"Starting file updates for {total_repos} repositories.")
        
        for repo in repos:
            try:
                logging.info(f"\n🔄 Processing repository: {repo.full_name}")
                
                default_branch = get_default_branch(repo)
                logging.info(f"Default branch for {repo.full_name}: {default_branch}")
                
                if search_and_update_files(repo, default_branch):
                    repos_updated += 1
                    logging.info(f"✅ Repository updated: {repo.full_name}")
                else:
                    logging.info(f"ℹ️ No updates needed for {repo.full_name}")
            
            except Exception as repo_error:
                logging.error(f"Error processing repository {repo.full_name}: {str(repo_error)}")
        
        logging.info("\n📊 Summary:")
        logging.info(f"Total repositories processed: {total_repos}")
        logging.info(f"Repositories updated: {repos_updated}")
        logging.info("🚀 Update process completed.")
    
    except Exception as main_error:
        logging.error(f"Critical error in main execution: {str(main_error)}")

if __name__ == "__main__":
    main()
