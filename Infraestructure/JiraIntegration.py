from Domain.Interfaces.IBoardIntegration import IBoardIntegration
from Domain.Models.Card import Card


class JiraIntegration(IBoardIntegration):
    
    def __init__(self, user_token: str):
        self.user_token = user_token


    def get_cards(self) -> list[Card]:
        print("Getting cards from Jira")

        return [
            Card("Card 1", "This is card 1", "tests", 1, 0),
            Card("Card 2", "This is card 2", "tests", 2, 0),
            Card("Card 3", "This is card 3", "tests", 3, 0),
        ]


    def update_card(self, card: Card) -> bool:
        print(f"Updating card: {card} from Jira")
        card.time_spent += 10
        pass
