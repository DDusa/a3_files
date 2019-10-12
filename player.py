"""Class for representing a Player entity within the game."""

__version__ = "1.1.0"

from game.entity import DynamicEntity


class Player(DynamicEntity):
    """A player in the game"""
    _type = 3

    def __init__(self, name: str = "Mario", max_health: float = 20):
        """Construct a new instance of the player.

        Parameters:
            name (str): The player's name
            max_health (float): The player's maximum & starting health
        """
        super().__init__(max_health=max_health)

        self._name = name
        self._score = 0

        self._on_tunnel = False
        self.invincible_time = 0

    def get_name(self) -> str:
        """(str): Returns the name of the player."""
        return self._name

    def get_score(self) -> int:
        """(int): Get the players current score."""
        return self._score

    def change_score(self, change: float = 1):
        """Increase the players score by the given change value."""
        self._score += change

    def change_health(self, change):
        if not (self.is_invincible() and change < 0):
            super().change_health(change)

    def invincible(self, time = 1000):
        self.invincible_time = time

    def step(self, time_delta, game_data):
        if self.is_invincible():
            self.invincible_time -= 1

    def is_invincible(self):
        return self.invincible_time > 0

    def on_tunnel(self, tunnel = None):
        self.tunnel = tunnel
        self._on_tunnel = True

    def off_tunnel(self):
        self._on_tunnel = False

    def is_on_tunnel(self):
        return self._on_tunnel

    def get_tunnel(self):
        return self.tunnel

    def __repr__(self):
        return f"Player({self._name!r})"
