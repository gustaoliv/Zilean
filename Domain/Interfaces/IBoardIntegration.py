import abc
from Domain.Models.Card import Card


class IBoardIntegration(metaclass = abc.ABCMeta):
    @abc.abstractmethod
    def get_cards(self) -> list[Card]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_timespent_to_card(self, card: Card) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def change_card_stage(self, card: Card, new_stage: str) -> bool:
        raise NotImplementedError()
    
    @abc.abstractmethod
    def refresh_card(self, card: Card) -> Card:
        raise NotImplementedError()