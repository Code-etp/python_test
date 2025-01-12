import os
from github import Github, GithubException
import logging
import time

# logging format
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# authentication and variable 
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"
WORKFLOW_PATH = ".github/workflows"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"
CREATE_PR = True

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set in the environment.")


g = Github(GITHUB_TOKEN)

def get_organization_repositories():
    """Get list of repositories from both organization and user."""
    try:
        repositories = []
        
        try:
            org = g.get_organization(ORG_NAME)
            logging.info(f"Found organization: {ORG_NAME}")
            repositories.extend(list(org.get_repos()))
        except GithubException as e:
            logging.warning(f"Could not access organization {ORG_NAME}, falling back to user repos: {str(e)}")
            
        user = g.get_user()
        logging.info(f"Authenticated as: {user.login}")
        user_repos = [repo for repo in user.get_repos() if repo.permissions.admin]
        
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

def search_and_update_workflow_files(repo, branch):
    """Search and update files only in .github/workflows directory."""
    try:
            
        contents = repo.get_contents(WORKFLOW_PATH, ref=branch)
        if not isinstance(contents, list):
            contents = [contents]
            
        updated = False
        for content in contents:
            if content.type == "file" and content.path.endswith(('.yml', '.yaml')):
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
                    logging.error(f"Error processing workflow file {content.path}: {str(e)}")
                    
        return updated
        
    except GithubException as e:
        if e.status == 404:
            logging.info(f"Workflows directory not found in {repo.name}")
        else:
            logging.error(f"Error accessing workflows in {repo.name}: {str(e)}")
        return False

def main():
    """Main function to process repositories and update workflow files."""
    try:
        repos = get_organization_repositories()
        
        total_repos = len(repos)
        repos_updated = 0
        
        logging.info(f"Starting workflow file updates for {total_repos} repositories.")
        
        for repo in repos:
            try:
                logging.info(f"\n🔄 Processing repository: {repo.full_name}")
                
                default_branch = get_default_branch(repo)
                logging.info(f"Default branch for {repo.full_name}: {default_branch}")
                
                if search_and_update_workflow_files(repo, default_branch):
                    repos_updated += 1
                    logging.info(f"✅ Repository updated: {repo.full_name}")
                else:
                    logging.info(f"ℹ️ No updates needed for {repo.full_name}")
            
            except Exception as repo_error:
                logging.error(f"Error processing repository {repo.full_name}: {str(repo_error)}")
        
        logging.info("\n📊 Summary:")
        logging.info(f"Total repositories processed: {total_repos}")
        logging.info(f"Repositories updated: {repos_updated}")
        logging.info("🚀 Workflow update process completed.")
    
    except Exception as main_error:
        logging.error(f"Critical error in main execution: {str(main_error)}")

if __name__ == "__main__":
    main()
