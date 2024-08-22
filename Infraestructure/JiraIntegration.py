from typing import Any
from Domain.Interfaces.IBoardIntegration import IBoardIntegration
from Domain.Models.Card import Card
from jira import JIRA, Issue
from jira.client import ResultList


class JiraIntegration(IBoardIntegration):
    
    def __init__(self, server: str, user_email: str, user_token: str):
        self.user_token: str = user_token
        self.jira: JIRA = JIRA(server=server, basic_auth=(user_email, user_token))


    def get_cards(self) -> list[Card]:
        myself = self.jira.myself()
        issues: dict[str, Any] | ResultList[Issue]  = self.jira.search_issues(jql_str=f"assignee='{myself['emailAddress']}' AND Sprint in openSprints() AND Sprint not in futureSprints()", maxResults=1000)
        if type(issues) == dict[str, Any]:
            return []

        issues = ResultList[Issue](issues)

        cards: list[Card] = []

        for issue in issues:
            issue_dict = dict(issue.raw)

            status = issue_dict["fields"]["status"]["name"]
            if status == "Concluído":
                continue

            duration = issue_dict["fields"]["aggregatetimeoriginalestimate"]
            if duration is None:
                duration = "0"

            time_spent = issue_dict["fields"]["aggregateprogress"]["progress"]
            if time_spent is None:
                time_spent = "0"

            card: Card = Card(id=issue.key, 
                              name=issue.fields.summary, 
                              epick=issue_dict["fields"]["parent"]["fields"]["summary"],
                              estimated_duration=int(duration),
                              time_spent=int(time_spent))
            cards.append(card)
            
        return cards


    def update_card(self, card: Card) -> bool:
        self.jira.add_worklog(card.id, timeSpentSeconds=card.time_spent)
        return True
