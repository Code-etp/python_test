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

def create_branch_name():
    """Create a unique branch name for the changes."""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"update-ecs-action-{random_suffix}"

def has_workflow_directory(repo):
    """Check if repository has a workflow directory."""
    try:
        repo.get_contents(WORKFLOW_PATH)
        return True
    except GithubException as e:
        if e.status == 404:
            return False
        raise

def list_workflow_files(repo):
    """List all workflow files in the repository."""
    workflow_files = []
    try:
        contents = repo.get_contents(WORKFLOW_PATH)
        if not isinstance(contents, list):
            contents = [contents]
        
        for content in contents:
            if content.path.endswith(('.yml', '.yaml')):
                workflow_files.append(content.path)
            elif content.type == "dir":
                # Recursively check subdirectories
                subcontents = repo.get_contents(content.path)
                if not isinstance(subcontents, list):
                    subcontents = [subcontents]
                for subcontent in subcontents:
                    if subcontent.path.endswith(('.yml', '.yaml')):
                        workflow_files.append(subcontent.path)
        
        return workflow_files
    except GithubException as e:
        logging.error(f"Error listing workflow files in {repo.name}: {str(e)}")
        return []

def check_file_content(repo, file_path):
    """Check if file contains the search string."""
    try:
        content = repo.get_contents(file_path)
        content_str = content.decoded_content.decode('utf-8')
        return SEARCH_STRING in content_str
    except Exception as e:
        logging.error(f"Error checking content in {file_path}: {str(e)}")
        return False

def update_workflow(repo_name, file_path, content, branch="main"):
    """Update the workflow file with the new ECS action version."""
    try:
        repo = g.get_repo(f"{ORG_NAME}/{repo_name}")
        file = repo.get_contents(file_path, ref=branch)
        
        # Decode content if it's base64 encoded
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        logging.info(f"Checking file: {file_path}")
        
        if SEARCH_STRING in content:
            logging.info(f"🔍 Found match in {repo_name}/{file_path}")
            updated_content = content.replace(SEARCH_STRING, REPLACE_STRING)
            
            if CREATE_PR:
                try:
                    # Create a new branch
                    new_branch = create_branch_name()
                    source_branch = repo.get_branch(branch)
                    ref = repo.create_git_ref(f"refs/heads/{new_branch}", source_branch.commit.sha)
                    logging.info(f"Created new branch: {new_branch}")
                    
                    # Commit changes to new branch
                    commit_message = f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}"
                    update_result = repo.update_file(
                        file_path,
                        commit_message,
                        updated_content,
                        file.sha,
                        branch=new_branch
                    )
                    logging.info(f"Committed changes to branch: {new_branch}")
                    
                    # Create pull request
                    pr = repo.create_pull(
                        title=f"Update ECS task definition to {REPLACE_STRING}",
                        body=f"Updates the ECS task definition action from {SEARCH_STRING} to {REPLACE_STRING}.\n\nAutomatically generated PR.",
                        head=new_branch,
                        base=branch
                    )
                    logging.info(f"✅ Created PR #{pr.number} in {repo_name}: {pr.html_url}")
                    return True
                except GithubException as e:
                    logging.error(f"❌ Failed to create PR for {repo_name}/{file_path}")
                    logging.error(f"Error details: {str(e)}")
                    return False
            else:
                # Direct commit to branch
                try:
                    result = repo.update_file(
                        file_path,
                        f"Update ECS task definition from {SEARCH_STRING} to {REPLACE_STRING}",
                        updated_content,
                        file.sha,
                        branch=branch
                    )
                    logging.info(f"✅ Successfully updated: {repo_name}/{file_path}")
                    return True
                except GithubException as e:
                    logging.error(f"❌ Failed to update {repo_name}/{file_path}")
                    logging.error(f"Error details: {str(e)}")
                    return False
        else:
            logging.info(f"ℹ️ No match found in: {repo_name}/{file_path}")
            return False
    except Exception as e:
        logging.error(f"❌ Unexpected error updating {repo_name}/{file_path}: {str(e)}")
        return False

def process_workflows(repo):
    """Process workflow files in a repository."""
    changes_made = False
    try:
        if not has_workflow_directory(repo):
            logging.info(f"ℹ️ No workflows directory in repo: {repo.name}")
            return False
            
        workflow_files = list_workflow_files(repo)
        logging.info(f"Found {len(workflow_files)} workflow files in {repo.name}")
        
        for file_path in workflow_files:
            logging.info(f"\nProcessing: {file_path}")
            try:
                content = repo.get_contents(file_path)
                if check_file_content(repo, file_path):
                    if update_workflow(repo.name, file_path, content.decoded_content):
                        changes_made = True
            except Exception as e:
                logging.error(f"❌ Error processing {file_path}: {str(e)}")
                
        return changes_made
    except Exception as e:
        logging.error(f"❌ Unexpected error in repo {repo.name}: {str(e)}")
        return False

def main():
    """Main function to update workflows."""
    try:
        # Try to authenticate as organization first, then as user
        try:
            org = g.get_organization(ORG_NAME)
            logging.info(f"🔑 Authenticated as organization: {org.login}")
        except GithubException:
            org = g.get_user(ORG_NAME)
            logging.info(f"🔑 Authenticated as user: {org.login}")
        
        # Track statistics
        total_repos = 0
        repos_with_workflows = 0
        updated_repos = 0
        
        logging.info(f"Mode: {'Creating PRs' if CREATE_PR else 'Direct commits'}")
        
        # Process each repository
        for repo in org.get_repos():
            total_repos += 1
            logging.info(f"\n📁 Processing repo: {repo.name}")
            
            if has_workflow_directory(repo):
                repos_with_workflows += 1
                if process_workflows(repo):
                    updated_repos += 1
        
        # Print summary
        logging.info("\n📊 Summary:")
        logging.info(f"Total repositories: {total_repos}")
        logging.info(f"Repositories with workflows: {repos_with_workflows}")
        logging.info(f"Repositories updated: {updated_repos}")
        logging.info(f"Repositories with workflows but unchanged: {repos_with_workflows - updated_repos}")
        
    except Exception as e:
        logging.error(f"❌ Error accessing account: {str(e)}")

if __name__ == "__main__":
    main()
