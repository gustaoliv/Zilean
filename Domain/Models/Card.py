class Card:
    def __init__(self, name: str, description: str, epick: str, estimated_duration: int, time_spent: int):
        self.name = name
        self.description = description
        self.epick = epick
        self.estimated_duration = estimated_duration
        self.time_spent = time_spent


    def __str__(self):
        return f"{self.name} - {self.description} - {self.epick} - {self.estimated_duration} - {self.time_spent}"