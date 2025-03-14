from dataclasses import dataclass


@dataclass
class Card:
    id: str
    name: str
    epick: str
    estimated_duration: int
    time_spent: int
    current_stage: str
    possible_next_stages: list[str]