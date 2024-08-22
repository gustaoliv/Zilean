from Business.BoardIntegrationBusiness import BoardIntegrationBusiness
from Infraestructure.JiraIntegration import JiraIntegration
import os
from dotenv import load_dotenv


load_dotenv()  # This line brings all environment variables from .env into os.environ


if __name__ == '__main__':
    server:str|None = os.environ.get("JIRA_SERVER")
    token: str|None = os.environ.get("JIRA_ACCESS_TOKEN")
    user_email: str|None = os.environ.get("JIRA_USER_EMAIL")
    if token is None or user_email is None or server is None:
        raise Exception("Could not load desired variables")
    
    business = BoardIntegrationBusiness(
        JiraIntegration(server, user_email, token)
    )
    business.run()
    