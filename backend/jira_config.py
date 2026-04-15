# JIRA_API_TOKEN lives in backend/.env (not here).
#
# If REST returns 401 but the Jira UI works: set JIRA_EMAIL in .env to the email shown at
# https://id.atlassian.com/manage-profile/manage-account (must match the account that created the API token).

JIRA_BASE_URL = "https://hackerearth.atlassian.net"
JIRA_EMAIL = "chaitanya.nath@hackerearth.com"
JIRA_PROJECT_KEY = "TCE"
JIRA_ISSUE_TYPE = "Content Tasks"
JIRA_ISSUE_TYPE_ID = ""
JIRA_SUMMARY_PREFIX = "[Content Plan]"
JIRA_BOARD_NAME = "Content Tasks"

# Map Content Dashboard status -> Jira transition *destination* names (first match wins).
# Your Jira workflow uses: To Do / In Progress / Blocked / Done
JIRA_STATUS_TO_JIRA_NAMES = {
    "open": ["To Do"],
    "in_progress": ["In Progress"],
    "blocked": ["Blocked"],
    "closed": ["Done"],
}
