import abc
from Domain.Models.Card import Card


class IBoardIntegration(metaclass = abc.ABCMeta):
    @abc.abstractmethod
    def get_cards(self) -> list[Card]:
        raise NotImplementedError()

    @abc.abstractmethod
    def update_card(self, card: Card) -> bool:
        raise NotImplementedError()

    
    