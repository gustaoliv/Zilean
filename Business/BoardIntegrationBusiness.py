from Domain.Interfaces.IBoardIntegration import IBoardIntegration


class BoardIntegrationBusiness:
    
    def __init__(self, board_integration: IBoardIntegration) -> None:
        self.board_integration = board_integration


    def run(self) -> None:
        cards = self.board_integration.get_cards()
        self.board_integration.update_card(cards[0])