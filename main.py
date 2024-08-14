from Business.BoardIntegrationBusiness import BoardIntegrationBusiness
from Infraestructure.JiraIntegration import JiraIntegration


if __name__ == '__main__':
    business = BoardIntegrationBusiness(
        JiraIntegration('token')
    )
    business.run()
    