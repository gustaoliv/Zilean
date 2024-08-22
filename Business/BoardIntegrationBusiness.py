from Domain.Interfaces.IBoardIntegration import IBoardIntegration


class BoardIntegrationBusiness:
    
    def __init__(self, board_integration: IBoardIntegration) -> None:
        self.board_integration = board_integration


    def run(self) -> None:
        cards = self.board_integration.get_cards()
        
        for card in cards:
            print(card)

        selected_id = input("Select a id: ")
        selected_card = [x for x in cards if x.id == selected_id][0]
        selected_card.time_spent += 100

        self.board_integration.update_card(selected_card)