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
        """Change health of the player but cant be reduced whrn invincible"""
        if not (self.is_invincible() and change < 0):
            super().change_health(change)

    def invincible(self, time = 1000):
        """Set invincible time to 1000*10ms when collect a star"""
        self.invincible_time = time

    def step(self, time_delta, game_data):
        """Run in steo function in main to reduce the time of invincible"""
        if self.is_invincible():
            self.invincible_time -= 1

    def is_invincible(self):
        """Return if the player is invincible"""
        return self.invincible_time > 0

    def on_tunnel(self, tunnel = None):
        """Set _on_tunnel variable to True if the player is on tunnel and record which tunnel player is on"""
        self.tunnel = tunnel
        self._on_tunnel = True

    def off_tunnel(self):
        """Set _on_tunnel variable to False if the player is off tunnel"""
        self.tunnel = None
        self._on_tunnel = False

    def is_on_tunnel(self):
        """Return if player is on tunnel"""
        return self._on_tunnel

    def get_tunnel(self):
        """return the which tunnel player is on"""
        return self.tunnel

    def __repr__(self):
        return f"Player({self._name!r})"
