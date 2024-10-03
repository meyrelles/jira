import local_class

my_board_name = "DI board"
cl = local_class.get_metadata(board_name=my_board_name)

my_board_id = cl.get_board_id()

# Get all sprints
sprints = cl.get_sprints()

filtered_sprints = [sprint for sprint in sprints if sprint.state in ['closed','active']]

# Sort closed sprints by their ID in descending order
sorted_closed_sprints = sorted(filtered_sprints, key=lambda sprint: sprint.id, reverse=True)

# Get the last 3 closed and active sprint (highest ID)
n_sprints = 3 if len(sorted_closed_sprints) >= 3 else len(sorted_closed_sprints)
last_3_sprint = sorted_closed_sprints[0:n_sprints]
cl.get_issues(sprint=last_3_sprint)

