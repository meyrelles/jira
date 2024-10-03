from jira import JIRA
import json
import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

def get_jira_credentials():

    # Environment variables for Azure Key Vault
    client_id = os.getenv('APP_CLIENT_ID')
    tenant_id = os.getenv('APP_TENANT_ID')
    client_secret = os.getenv('APP_SECRET')

    # Azure Key Vault name and secret name
    key_vault_name = 'kvGeolog'  
    secret_name = 'DATA-INTEGRATION-JIRA-TOKEN'  

    # Construct the Key Vault URL
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    # Authenticate using environment variables
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    client = SecretClient(vault_url=key_vault_url, credential=credential)

    # Retrieve the Jira token from Azure Key Vault
    jira_token_secret = client.get_secret(secret_name)
    return eval(jira_token_secret.value)

class get_metadata():
    def __init__(self, **context) -> None:
        self.board_name = context["board_name"]
        with open('jira_configs.json', 'r') as file:
            configs = json.load(file)

        jira_token = get_jira_credentials()
        # Extract credentials from the loaded JSON data
        jira_url = configs['jira_url']
        username = jira_token[0]
        api_token = jira_token[1]

        # Authenticate to Jira
        self.jira = JIRA(server=jira_url, basic_auth=(username, api_token))


    def get_board_id(self):
        # List all boards
        boards = self.jira.boards()

        return ([board.id for board in boards if board.name == self.board_name])[0]
    
    def get_sprints(self):
        # Get all sprints for the specified board
        sprints = self.jira.sprints(self.get_board_id())

        return sprints
    
    def get_issues(self, **context):

        sprints_list = context["sprint"]
        # Fetch issues in the selected sprints
        for sprint in sprints_list:
            jql = f'sprint = {sprint.id}'
            stories = self.jira.search_issues(jql)

            # Print details of the stories
            for issue in stories:
                # print(f"Issue Key: {issue.key}")
                # for field_name, field_value in issue.fields.__dict__.items():
                #     print(f"{field_name}: {field_value}")
                print(f'Sprint Name: {sprint.name} / id: {sprint.id}')
                print(f'Issue ID: {issue.key}')
                print(f'Summary: {issue.fields.summary}')
                print(f'Status: {issue.fields.status.name}')
                team_start_date = getattr(issue.fields, 'customfield_10080', 'No Team start date')
                team_end_date = getattr(issue.fields, 'customfield_10081', 'No Team end date')
                print(f'Team start date: {team_start_date}')
                print(f'Team end date: {team_end_date}')
                print(f'Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"}')
                start_date = sprint.startDate if hasattr(sprint, 'startDate') else 'No start date'
                end_date = sprint.endDate if hasattr(sprint, 'endDate') else 'No end date'
                print(f'Sprint start date: {start_date}')
                print(f'Sprint end date: {end_date}')
                story_points = getattr(issue.fields, 'customfield_10016', 'No Story Points') 
                print(f"Story Points: {story_points}")
                print('-' * 40)
