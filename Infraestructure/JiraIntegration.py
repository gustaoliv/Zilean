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

            transitions = self.jira.transitions(issue)
            if transitions == None or len(transitions) == 0:
                transitions = []
            else:
                transitions = [str(transition["to"]["name"]).capitalize() for transition in transitions]

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
                              time_spent=int(time_spent),
                              current_stage=issue_dict["fields"]["status"]["name"].capitalize(),
                              possible_next_stages=transitions)
            cards.append(card)
            
        return cards


    def add_timespent_to_card(self, card: Card) -> bool:
        self.jira.add_worklog(card.id, timeSpentSeconds=card.time_spent)
        return True


    def change_card_stage(self, card: Card, new_stage: str) -> bool:
        issue: Issue = self.jira.issue(card.id)
        card_transitions = self.jira.transitions(issue)
        transition_id = [transition["id"] for transition in card_transitions if str(transition["to"]["name"]).capitalize() == new_stage][0]
        self.jira.transition_issue(card.id, transition_id)
        return True
    

    def refresh_card(self, card: Card) -> Card:
        issue: Issue = self.jira.issue(card.id)
        issue_dict = dict(issue.raw)

        transitions = self.jira.transitions(issue)
        if transitions == None or len(transitions) == 0:
            transitions = []
        else:
            transitions = [str(transition["to"]["name"]).capitalize() for transition in transitions]

        status = issue_dict["fields"]["status"]["name"]
        if status == "Concluído":
            return card

        duration = issue_dict["fields"]["aggregatetimeoriginalestimate"]
        if duration is None:
            duration = "0"

        time_spent = issue_dict["fields"]["aggregateprogress"]["progress"]
        if time_spent is None:
            time_spent = "0"

        refreshed_card: Card = Card(id=issue.key,
                          name=issue.fields.summary,
                          epick=issue_dict["fields"]["parent"]["fields"]["summary"],
                          estimated_duration=int(duration),
                          time_spent=int(time_spent),
                          current_stage=issue_dict["fields"]["status"]["name"].capitalize(),
                          possible_next_stages=transitions)
        return refreshed_card