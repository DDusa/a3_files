"""
Simple 2d world where the player can interact with the items in the world.
"""

__author__ = ""
__date__ = ""
__version__ = "1.1.0"
__copyright__ = "The University of Queensland, 2019"

import math
import tkinter as tk

from typing import Tuple, List

from tkinter import filedialog
from tkinter import messagebox
from game.util import get_collision_direction

import pymunk

from game.block import Block, MysteryBlock
from game.entity import Entity, BoundaryWall
from game.mob import Mob, CloudMob, Fireball
from game.item import DroppedItem, Coin
from game.view import GameView, ViewRenderer
from game.world import World



from level import load_world, WorldBuilder
from player import Player

BLOCK_SIZE = 2 ** 4
MAX_WINDOW_SIZE = (1080, math.inf)

MARIO_VEL = {
    "vx": 200,
    "vy": -200
}

GOAL_SIZES = {
    "flag": (0.2, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    'b': "bounce_block",
    '^': 'cube'
}

ITEMS = {
    'C': 'coin'
}

MOBS = {
    '&': "cloud",
    '@': "mushroom",
    '*': "star",
    'I': "flag",
    '=': "tunnel",
    'S': "switch",

}


def create_block(world: World, block_id: str, x: int, y: int, *args):
    """Create a new block instance and add it to the world based on the block_id.

    Parameters:
        world (World): The world where the block should be added to.
        block_id (str): The block identifier of the block to create.
        x (int): The x coordinate of the block.
        y (int): The y coordinate of the block.
    """
    block_id = BLOCKS[block_id]
    if block_id == "mystery_empty":
        block = MysteryBlock()
    elif block_id == "mystery_coin":
        block = MysteryBlock(drop="coin", drop_range=(3, 6))
    elif block_id == "bounce_block":
        block = BounceBlock()
    elif block_id == "flag":
        block = Flag()
    elif block_id == "tunnel":
        block = Tunnel()
    elif block_id == "switch":
        block = Switch()
    elif block_id == "switch_pressed":
        block = Switch(pressed = True)
    else:
        block = Block(block_id)

    world.add_block(block, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_item(world: World, item_id: str, x: int, y: int, *args):
    """Create a new item instance and add it to the world based on the item_id.

    Parameters:
        world (World): The world where the item should be added to.
        item_id (str): The item identifier of the item to create.
        x (int): The x coordinate of the item.
        y (int): The y coordinate of the item.
    """
    item_id = ITEMS[item_id]
    if item_id == "coin":
        item = Coin()
    elif item_id == "star":
        item = Star()
    else:
        item = DroppedItem(item_id)

    world.add_item(item, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_mob(world: World, mob_id: str, x: int, y: int, *args):
    """Create a new mob instance and add it to the world based on the mob_id.

    Parameters:
        world (World): The world where the mob should be added to.
        mob_id (str): The mob identifier of the mob to create.
        x (int): The x coordinate of the mob.
        y (int): The y coordinate of the mob.
    """
    mob_id = MOBS[mob_id]
    if mob_id == "cloud":
        mob = CloudMob()
    elif mob_id == "fireball":
        mob = Fireball()
    elif mob_id == "mushroom":
        mob = Mushroom()
    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))


BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
    "bounce_block": "bounce_block"
}

ITEM_IMAGES = {
    "coin": "coin_item"
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down",
    "mushroom": "mushroom",
    "star": "star",
    "flag": "flag",
    "tunnel": "tunnel",
    "switch": "switch"
}


class MarioViewRenderer(ViewRenderer):
    """A customised view renderer for a game of mario."""

    @ViewRenderer.draw.register(Player)
    def _draw_player(self, instance: Player, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:

        if shape.body.velocity.x >= 0:
            image = self.load_image("mario_right")
        else:
            image = self.load_image("mario_left")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="player")]

    @ViewRenderer.draw.register(MysteryBlock)
    def _draw_mystery_block(self, instance: MysteryBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("coin")
        else:
            image = self.load_image("coin_used")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]


class MarioApp:
    """High-level app class for Mario, a 2d platformer"""

    _world: World

    def __init__(self, master: tk.Tk):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self._master = master

        world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, 300), fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder

        self._player = Player(max_health=5)
        self.reset_world('level1.txt')

        self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
        self._view = GameView(master, size, self._renderer)
        self._view.pack()

        self.bind()

        #Create the title and menu
        master.title("Mario")
        self.menu()
        self._status_bar = StatusBar(master,score = self._player.get_score(),
                                    health = self._player.get_health())

        # Wait for window to update before continuing
        master.update_idletasks()
        self.step()

    def menu(self):
        menubar = tk.Menu(self._master)
        self._master.config(menu=menubar)
        filemenu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="Load Level", command=self.load_window)
        filemenu.add_command(label="Reset Level", command=self.reset_level)
        filemenu.add_command(label="Exit", command=self.exit)

    def reset_world(self, new_level="level1.txt"):
        self._world = load_world(self._builder, new_level)
        self._world.add_player(self._player, BLOCK_SIZE, BLOCK_SIZE)
        self._builder.clear()

        self._setup_collision_handlers()

    def bind(self):
        """Bind all the keyboard events to their event handlers."""
        self._master.bind("<Key>", self._move_event)

    def _move_event(self, event):
        if event.keysym == 'Right' or event.keysym == 'r':
            vx = MARIO_VEL['vx']
            vy = self._player.get_velocity()[1]
            self._move(vx, vy)
            print('r')
        elif event.keysym == 'Left' or event.keysym == 'l':
            vx = -MARIO_VEL['vx']
            vy = self._player.get_velocity()[1]
            self._move(vx, vy)
            print('l')
        elif event.keysym == 'Up' or event.keysym == 'w' or event.keysym == 'space':
            self._jump()
            print('u')
        elif event.keysym == 'Down' or event.keysym == 's':
            self._duck()
            print('d')

    def load_window(self):

        self.load_input = tk.Entry(self._master, width=20)
        self.load_input.pack()
        self.load_button = tk.Button(self._master, text="Load", command=self.load_level)
        self.load_button.pack()

    def load_level(self):
        filename = self.load_input.get()
        self.reset_level(filename)

        self.load_input.destroy()
        self.load_button.destroy()

    def reset_level(self, new_level="level1.txt"):
        self._player = Player(max_health=5)
        self.reset_world(new_level)

    def dead_ask_reset(self):
        if self._player.is_dead():
             reply = messagebox.askquestion(type=messagebox.YESNO,
                                            title="You are dead!",
                                            message="Would you like to restart the level?")
             if reply == messagebox.YES :
                 self.reset_level() # can_close is already True.
             elif reply == messagebox.NO :
                 self.exit()

    def exit(self):
        self._master.destroy()

    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)

        self._view.draw_entities(self._world.get_all_things())

    def scroll(self):
        """Scroll the view along with the player in the center unless
        they are near the left or right boundaries
        """
        x_position = self._player.get_position()[0]
        half_screen = self._master.winfo_width() / 2
        world_size = self._world.get_pixel_size()[0] - half_screen

        # Left side
        if x_position <= half_screen:
            self._view.set_offset((0, 0))

        # Between left and right sides
        elif half_screen <= x_position <= world_size:
            self._view.set_offset((half_screen - x_position, 0))

        # Right side
        elif x_position >= world_size:
            self._view.set_offset((half_screen - world_size, 0))

    def step(self):
        """Step the world physics and redraw the canvas."""
        data = (self._world, self._player)
        self._world.step(data)

        self._status_bar.update_status(self._player.get_health(), self._player.get_score())
        self.dead_ask_reset()

        self.scroll()
        self.redraw()

        self._master.after(10, self.step)

    def _move(self, dx, dy):
        self._player.set_velocity([dx,dy])

    def _jump(self):
        vx,vy = self._player.get_velocity()
        if(vy == 0):
            vy = MARIO_VEL['vy']
        self._player.set_velocity([vx, vy])

    def _duck(self):
        pass

    def _setup_collision_handlers(self):
        self._world.add_collision_handler("player", "item", on_begin=self._handle_player_collide_item)
        self._world.add_collision_handler("player", "block", on_begin=self._handle_player_collide_block,
                                          on_separate=self._handle_player_separate_block)
        self._world.add_collision_handler("player", "mob", on_begin=self._handle_player_collide_mob)
        self._world.add_collision_handler("mob", "block", on_begin=self._handle_mob_collide_block)
        self._world.add_collision_handler("mob", "mob", on_begin=self._handle_mob_collide_mob)
        self._world.add_collision_handler("mob", "item", on_begin=self._handle_mob_collide_item)

    def _handle_mob_collide_block(self, mob: Mob, block: Block, data,
                                  arbiter: pymunk.Arbiter) -> bool:
        if mob.get_id() == "fireball":
            if block.get_id() == "brick":
                self._world.remove_block(block)
            self._world.remove_mob(mob)

        if mob.get_id() == "mushroom":
            mob.collide(block)
        return True

    def _handle_mob_collide_item(self, mob: Mob, block: Block, data,
                                 arbiter: pymunk.Arbiter) -> bool:
        return False

    def _handle_mob_collide_mob(self, mob1: Mob, mob2: Mob, data,
                                arbiter: pymunk.Arbiter) -> bool:
        if mob1.get_id() == "fireball" or mob2.get_id() == "fireball":
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)
        if mob1.get_id() == "mushroom":
            mob1.collide(mob2)
        if mob2.get_id() == "mushroom":
            mob2.collide(mob1)


        return False

    def _handle_player_collide_item(self, player: Player, dropped_item: DroppedItem,
                                    data, arbiter: pymunk.Arbiter) -> bool:
        """Callback to handle collision between the player and a (dropped) item. If the player has sufficient space in
        their to pick up the item, the item will be removed from the game world.

        Parameters:
            player (Player): The player that was involved in the collision
            dropped_item (DroppedItem): The (dropped) item that the player collided with
            data (dict): data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter): Data about a collision
                                      (see http://www.pymunk.org/en/latest/pymunk.html#pymunk.Arbiter)
                                      NOTE: you probably won't need this
        Return:
             bool: False (always ignore this type of collision)
                   (more generally, collision callbacks return True iff the collision should be considered valid; i.e.
                   returning False makes the world ignore the collision)
        """

        dropped_item.collect(self._player)
        self._world.remove_item(dropped_item)
        return False

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:

        block.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        mob.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        return True





class StatusBar(tk.Frame):
    BARHEIGHT = 20
    def __init__(self, master, score, health, max_health = 5):

        self.health = health
        self.max_health = max_health
        self.score = score
        self.width = MAX_WINDOW_SIZE[0]

        self.canvas = tk.Canvas(master, width = self.width, height = self.BARHEIGHT, bg ='black',  highlightthickness = 0, borderwidth = 0)
        self.display_health()
        self.canvas.pack()

        self._score = tk.Label(master, text="Score: {0}".format(score))
        self._score.pack()

    def display_health(self):
        health_percent = self.health/self.max_health
        if health_percent > 0.5:
            color = 'green'
        elif health_percent > 0.25:
            color = 'orange'
        else:
            color = 'red'
        self.canvas.create_rectangle(0, 0, health_percent * self.width, self.BARHEIGHT , fill= color)

    def update_status(self, health, score):

        self.canvas.delete("all")
        self.health = health
        self.display_health()
        self._score.config(text = "Score: {0}".format(score))


class Mushroom(Mob):

    _id = "mushroom"

    def __init__(self):
        super().__init__(self._id, size=(16, 16), weight=300, tempo=100)

    def on_hit(self, event: pymunk.Arbiter, data):

        world, player = data
        player_vx, player_vy = player.get_velocity()

        if get_collision_direction(player, self) != "A":
            self.collide(player)
            player.change_health(-1)
            if(player_vx > 0):
                player.set_velocity([-100,player_vy])
            else:
                player.set_velocity([100,player_vy])
        else:
            player.set_velocity([player_vx, 200])
            world.remove_mob(self)

    def collide(self, entity):
        if get_collision_direction(entity, self) == "R" or \
                get_collision_direction(entity, self) == "L":
            self.set_tempo(-self.get_tempo())


class BounceBlock(Block):
    _id = "bounce_block"

    def __init__(self):
        super().__init__()

    def on_hit(self, event, data):
        world, player = data
        if get_collision_direction(player, self) == "A":
            vx = data[1].get_velocity()[0]
            vy = -300
            data[1].set_velocity([vx, vy])


class Star(DroppedItem):

    _id = "star"

    def collect(self, player: Player):
        player.invincible()

class Flag(Block):

    def on_hit(self, event, data):
        """Callback collision with player event handler."""
        world, player = data




class Tunnel(Block):
    pass

class Switch(Block):
    pass

def main():
    root = tk.Tk()
    app = MarioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
