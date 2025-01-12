import os
from github import Github, GithubException
import logging
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "lahteeph"
WORKFLOW_PATH = ".github/workflows/"
SEARCH_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v1"
REPLACE_STRING = "aws-actions/amazon-ecs-deploy-task-definition@v2"
CREATE_PR = False

def check_rate_limit(g):
    rate_limit = g.get_rate_limit()
    remaining = rate_limit.core.remaining
    if remaining < 10:
        reset_time = rate_limit.core.reset
        sleep_time = (reset_time - datetime.datetime.utcnow()).total_seconds() + 1
        logging.info(f"Rate limit low. Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)
    return remaining

def process_workflow_file(repo, file_content, branch):
    try:
        decoded_content = file_content.decoded_content.decode('utf-8')
        if SEARCH_STRING in decoded_content:
            updated_content = decoded_content.replace(SEARCH_STRING, REPLACE_STRING)
            if CREATE_PR:
                branch_name = f"update-ecs-action-{int(time.time())}"
                source_branch = repo.get_branch(branch)
                repo.create_git_ref(f"refs/heads/{branch_name}", source_branch.commit.sha)
                repo.update_file(
                    file_content.path,
                    f"Update {SEARCH_STRING} to {REPLACE_STRING}",
                    updated_content,
                    file_content.sha,
                    branch=branch_name
                )
                repo.create_pull(
                    title=f"Update ECS deploy action to v2",
                    body=f"Updates {SEARCH_STRING} to {REPLACE_STRING}",
                    head=branch_name,
                    base=branch
                )
            else:
                repo.update_file(
                    file_content.path,
                    f"Update {SEARCH_STRING} to {REPLACE_STRING}",
                    updated_content,
                    file_content.sha,
                    branch=branch
                )
            return True
    except Exception as e:
        logging.error(f"Error processing workflow file {file_content.path}: {str(e)}")
    return False

def main():
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    g = Github(GITHUB_TOKEN)
    updated_repos = []
    
    try:
        org = g.get_organization(ORG_NAME)
        repos = list(org.get_repos())
        logging.info(f"Found {len(repos)} repositories")

        for repo in repos:
            try:
                check_rate_limit(g)
                logging.info(f"Processing {repo.full_name}")
                
                try:
                    workflow_contents = repo.get_contents(WORKFLOW_PATH)
                    if not isinstance(workflow_contents, list):
                        workflow_contents = [workflow_contents]
                        
                    for content in workflow_contents:
                        if content.type == "file" and content.path.endswith(('.yml', '.yaml')):
                            if process_workflow_file(repo, content, repo.default_branch):
                                updated_repos.append(repo.full_name)
                                logging.info(f"Updated workflow in {repo.full_name}")
                                
                except GithubException as e:
                    if e.status == 404:
                        logging.info(f"No workflow directory found in {repo.full_name}")
                    else:
                        logging.error(f"Error accessing {repo.full_name}: {str(e)}")
                        
            except Exception as e:
                logging.error(f"Error processing repository {repo.full_name}: {str(e)}")
                
        logging.info(f"\nSummary:")
        logging.info(f"Total repositories processed: {len(repos)}")
        logging.info(f"Repositories updated: {len(updated_repos)}")
        if updated_repos:
            logging.info("Updated repositories:")
            for repo_name in updated_repos:
                logging.info(f"- {repo_name}")
                
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
