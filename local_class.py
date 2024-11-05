from jira import JIRA
import json
import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar

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

# Function to read the log file and convert its contents to a list of dictionaries for each story
def log_to_dict_list(file_path):
    stories = []
    story_data = {}

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line == "----------------------------------------":
                # When encountering the separator, save the current story and reset for the next one
                if story_data:
                    stories.append(story_data)
                    story_data = {}
            elif line:
                # Only process lines with a colon
                if ':' in line:
                    key, value = line.split(':', 1)
                    # Convert "None" string to an actual None type
                    value = None if value.strip() == 'None' else value.strip()
                    story_data[key.strip()] = value
                else:
                    # If line has no colon, store it with None as value
                    story_data[line] = None  

    # Add the last story if the file doesn't end with the separator
    if story_data:
        stories.append(story_data)

    return stories

def get_end_date():
    # Define a container for the selected date
    selected_date = None

    # Function to handle the date selection
    def on_date_select():
        nonlocal selected_date
        selected_date = cal.get_date()
        root.destroy()

    # Set up the main tkinter window
    root = tk.Tk()
    root.title("Select End Date")

    # Set up the calendar widget
    cal = Calendar(root, selectmode="day", date_pattern="mm/dd/yy")
    cal.pack(pady=20)

    # Add a button to confirm the selection
    ttk.Button(root, text="Select Date", command=on_date_select).pack(pady=10)

    # Run the tkinter main loop
    root.mainloop()

    # Convert the selected date to datetime in the desired format
    if selected_date:
        try:
            end_date = datetime.strptime(selected_date, "%m/%d/%y")
            return end_date
        except ValueError:
            print("Invalid date format.")
            return None
    else:
        return None

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

        start_dates=[]
        end_dates=[]

        with open("return.log", "w") as log_file:
            # Fetch issues in the selected sprints
            for sprint in sprints_list:
                jql = f'sprint = {sprint.id}'
                stories = self.jira.search_issues(jql)

                # Write details of the stories to the file
                for issue in stories:
                    log_file.write(f'Sprint Name: {sprint.name} / id: {sprint.id}\n')
                    log_file.write(f'Issue ID: {issue.key}\n')
                    log_file.write(f'Summary: {issue.fields.summary}\n')
                    log_file.write(f'Status: {issue.fields.status.name}\n')
                    
                    team_start_date = getattr(issue.fields, 'customfield_10080', 'No Team start date')
                    team_end_date = getattr(issue.fields, 'customfield_10081', 'No Team end date')
                    
                    log_file.write(f'Team start date: {team_start_date}\n')
                    log_file.write(f'Team end date: {team_end_date}\n')
                    log_file.write(f'Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"}\n')
                    
                    start_date = sprint.startDate if hasattr(sprint, 'startDate') else 'No start date'
                    end_date = sprint.endDate if hasattr(sprint, 'endDate') else 'No end date'
                    
                    log_file.write(f'Sprint start date: {start_date}\n')
                    log_file.write(f'Sprint end date: {end_date}\n')
                    
                    story_points = getattr(issue.fields, 'customfield_10016', 'No Story Points')
                    log_file.write(f"Story Points: {story_points}\n")
                    log_file.write(f'User Blocked date: {getattr(issue.fields, 'customfield_10144', None)}\n')
                    log_file.write('-' * 40 + '\n')

                    if team_start_date:
                        start_dates.append(datetime.strptime(team_start_date, '%Y-%m-%dT%H:%M:%S.%f%z'))
                    if team_end_date:
                        end_dates.append(datetime.strptime(team_end_date, '%Y-%m-%dT%H:%M:%S.%f%z'))

    def stories_list(self):
        activity = {}

        last_report_date = get_end_date()

        # Path to the log file
        file_path = 'return.log'

        # Convert the log file content to a list of dictionaries
        log_data_list = log_to_dict_list(file_path)
        for i, story in enumerate(log_data_list):
            start_date = end_date = block_date = story_id = story_desc = None

            if log_data_list[i]['Team start date']:
                start_date = datetime.strptime(log_data_list[i]['Team start date'].split("T")[0], '%Y-%m-%d')

            if log_data_list[i]['Team end date']:
                end_date = datetime.strptime(log_data_list[i]['Team end date'].split("T")[0], '%Y-%m-%d')

            if log_data_list[i]['User Blocked date']:
                block_date = datetime.strptime(log_data_list[i]['User Blocked date'].split("T")[0], '%Y-%m-%d')

            story_id = log_data_list[i]['Issue ID']
            story_desc = log_data_list[i]['Summary']
            story_summary = f"{story_id} - {story_desc}"
            
            if "BLOCKED" in log_data_list[i]['Status'].upper():
                end_date = block_date

            if not end_date:
                end_date = datetime.strptime(str(last_report_date).split()[0], '%Y-%m-%d')

            # Calculate date range and aggregate unique tasks per date
            if start_date:
                n_d_st = (end_date - start_date).days
                for dt in range(n_d_st + 1):
                    date_ = start_date + timedelta(days=dt)
                    date_str = date_.strftime('%Y-%m-%d')

                    # Initialize the date entry if it does not exist, using a set to avoid duplicates
                    if date_str not in activity:
                        activity[date_str] = set()
                    
                    activity[date_str].add(story_summary)

        # Print the sorted activity log with unique tasks
        for date_key in sorted(activity.keys()):
            print(f"{date_key}")
            tasks = '\n'.join(task.strip() for task in activity[date_key])
            print(tasks)
