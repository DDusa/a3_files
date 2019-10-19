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
import os
from PIL import Image

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
    "vx": 100,
    "vy": -200
}

GOAL_SIZES = {
    "flag": (2, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    'b': "bounce_block",
    '^': 'cube',
    'I': "flag",
    '=': "tunnel",
    'S': "switch"
}

ITEMS = {
    'C': 'coin',
    '*': "star"
}

MOBS = {
    '&': "cloud",
    '@': "mushroom"

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
    "bounce_block": "bounce_block" ,
    "flag": "flag",
    "tunnel": "tunnel",
    "switch": "switch"
}

ITEM_IMAGES = {
    "coin": "coin_item",
    "star": "star"
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down",
    "mushroom": "mushroom",
}


class MarioApp:
    """High-level app class for Mario, a 2d platformer"""

    _world: World

    def __init__(self, master: tk.Tk):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self._master = master

        # Wait for window to update before continuing
        master.update_idletasks()

        self.load_config()
        self.status_var_config()

        world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, self.configuration["gravity"]), fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder

        self._level = self.configuration["start"]
        if "character" in self.configuration:
            self.character = self.configuration["character"]
        else:
            self.character = "Mario"
        self._player = Player(name = self.character, max_health=self.configuration["health"])

        self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

        self.reset_world(self._level)
        self.bind()


        master.title("Mario")
        self.menu()
        self._status_bar = StatusBar(master, self._player)


        self.step()

    def status_var_config(self):
        """
            Initialize the variables representing status of the game
        """

        self._pause = False
        self._exit = False
        self.pressed_swtich_list = []
        self.invisible_list = []

    def load_config(self):
        """
            Load configuration from file
        """

        self.configuration = {}

        config_filename = filedialog.askopenfilename()
        try:
            self.config_file_content = open(config_filename, "r").readlines()
        except:
            self.configuration_error('missing')


        for line_content in self.config_file_content:
            self.find_in_line_and_config(line_content, "gravity", int)
            self.find_in_line_and_config(line_content, "start", str)
            self.find_in_line_and_config(line_content, "character", str)
            self.find_in_line_and_config(line_content, "x", int)
            self.find_in_line_and_config(line_content, "y", int)
            self.find_in_line_and_config(line_content, "mass", int)
            self.find_in_line_and_config(line_content, "health", int)
            self.find_in_line_and_config(line_content, "max_velocity", int)

        self.check_config("gravity", "start", "x",
                          "y","mass", "health",
                          "max_velocity", "start")

    def check_config(self, *args):
        """
        Check if there is configuration not valid load from the file

        Args: *args :the configuration name to be checked.
        """
        for key_name in args:
            if key_name not in self.configuration:
                self.configuration_error('invalid')

    def find_in_line_and_config(self, line_content, string_to_find_, val_type, ):
        """
        Find a configuration type in one line and set it to configuaration with val_type if found

        Args:
            line_content: the line to find the string in
            string_to_find_: the string to find
            val_type:

        Returns: True if string found, False if not found.

        """
        index = line_content.find(":")
        if string_to_find_ == line_content[0: index].strip():
            try:
                self.configuration[string_to_find_] = val_type(line_content[index + 1:].strip())
            except:
                self.configuration_error('cannot be parsed')
            return True
        else:
            return False

    def configuration_error(self, error):
        """
        Deal with configuartion error information show.

        Args:
            error: errroe type in string
        """
        if error == 'missing':
            messagebox.showinfo("CONFIGURE ERROR","Configuration missing!")
        if error == 'invalid':
            messagebox.showinfo("CONFIGURE ERROR","Configuration invalid!")
        if error == 'cannot be parsed':
            messagebox.showinfo("CONFIGURE ERROR","Configuration cannot be parsed!")
        exit(0)

    def menu(self):
        """
            Add menu bar to the game
        """
        menubar = tk.Menu(self._master)
        self._master.config(menu=menubar)

        filemenu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="Load Level", command=self.load_level)
        filemenu.add_command(label="Reset Level", command=self.reset_level)
        filemenu.add_command(label="Edit Level", command=self.edit_level)
        filemenu.add_command(label="Exit", command=self.exit)

        gamemenu = tk.Menu(menubar)
        menubar.add_cascade(label="Game", menu=gamemenu)
        gamemenu.add_command(label="Pause", command=self.pause)
        gamemenu.add_command(label="Continue", command=self.resume)
        gamemenu.add_command(label="High Score", command=self.read_highscore)

    def edit_level(self):
        """
            Pause the game
        """
        self.pause()
        self.mapeditor_level = tk.Toplevel()
        self.mapeditor_level.title("Level editor")
        self.map_edited = True
        self.new_level_button = tk.Button(self.mapeditor_level, text="New level", command=self.create_new, width = 20,height = 5)
        self.new_level_button.pack(side = tk.LEFT, padx= 2, pady = (3,2))

        self.edit_level_button = tk.Button(self.mapeditor_level, text="Edit level", command=self.edit_old, width = 20,height = 5)
        self.edit_level_button.pack(side = tk.LEFT, padx= 2, pady = (3,2))

        self.mapeditor_level.protocol("WM_DELETE_WINDOW", self.edit_level_closing)

    def create_new(self):
        self.new_level_button.destroy()
        self.edit_level_button.destroy()

        self.level_name_label = tk.Label(self.mapeditor_level, text='Name of new level(.txt): ', width=20)
        self.level_name_label.grid(row = 0)
        self.level_name_entry = tk.Entry(self.mapeditor_level, width=40)
        self.level_name_entry.grid(row=0, column=1)

        self.level_width_label = tk.Label(self.mapeditor_level, text='The width of new level: ', width=20)
        self.level_width_label.grid(row = 1)
        self.level_width_entry = tk.Entry(self.mapeditor_level, width=40)
        self.level_width_entry.grid(row=1, column=1)

        self.level_height_label = tk.Label(self.mapeditor_level, text='The height of new level: ', width=20)
        self.level_height_label.grid(row = 2)
        self.level_height_entry = tk.Entry(self.mapeditor_level, width=40)
        self.level_height_entry.grid(row=2, column=1)

        self.next_button = tk.Button(self.mapeditor_level, text="Next", command=self.create_new_level, width=20)
        self.next_button.grid(row=0, column=2, rowspan = 3, sticky= tk.W + tk.E + tk.N + tk.S)

    def create_new_level(self):
        if not self.level_name_entry.get():
            messagebox.showinfo("Create error","Level name can't be None!")
        else:
            self.editing_level_name = self.level_name_entry.get()
            try:
                 open(self.editing_level_name, "r")
                 if messagebox.askokcancel("Edit error","The file has existed, do you want to edit?"):
                     level_existed = True
                     edit_exist = True
                 else:
                     level_existed = True
                     edit_exist = False
            except:
                level_existed = False
                try:
                    new_level_width = int(self.level_width_entry.get())
                    width_invalid = False
                    try:
                        new_level_height = int(self.level_height_entry.get())
                        height_invalid = False
                    except:
                        messagebox.showinfo("Create error", "Level height must be a int!")
                        height_invalid = True
                except:
                    messagebox.showinfo("Create error", "Level width must be a int!")
                    width_invalid = True


            if level_existed:
                if edit_exist:
                    self.edit_map(self.editing_level_name)
                else:
                    self.create_new()
            else:
                if width_invalid:
                    pass
                elif height_invalid:
                    pass
                else:
                    file = open(self.editing_level_name, "w+")
                    for line in range(0,new_level_height):
                        file.write(new_level_width * " " + "\n")
                        if line == new_level_height - 1:
                            file.write(new_level_width * "%" + "\n" )
                            file.close()

                    self.level_name_label.destroy()
                    self.level_name_entry.destroy()
                    self.level_width_label.destroy()
                    self.level_width_entry.destroy()
                    self.level_height_label.destroy()
                    self.level_height_entry.destroy()
                    self.next_button.destroy()
                    self.edit_map(self.editing_level_name)

    def edit_old(self):


        self.editing_level_name = filedialog.askopenfilename()
        try:

            open(self.editing_level_name, "r")
            self.new_level_button.destroy()
            self.edit_level_button.destroy()
            level_existed = True
        except:
            messagebox.showinfo("Edit error", "Wrong level name!")
            level_existed = False

        if level_existed :
            self.edit_map(self.editing_level_name)

    def edit_map(self, level_to_edit):
        #read the file to edit and save
        #view of editor
        map_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, self.configuration["gravity"]), fallback=create_unknown)
        map_builder.register_builders(BLOCKS.keys(), create_block)
        map_builder.register_builders(ITEMS.keys(), create_item)
        map_builder.register_builders(MOBS.keys(), create_mob)
        self._map_builder = map_builder
        self._map = load_world(self._map_builder, level_to_edit)
        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._map.get_pixel_size())))
        self._map_view = GameView(self.mapeditor_level, size, self._renderer)
        self._map_view.pack()

        self._map_view.delete(tk.ALL)
        self._map_view.draw_entities(self._map.get_all_things())

        self.create_block_button = {}
        self.add_create_block("tunnel")
        self.add_create_block("flag_block")
        self.add_create_block("coin")
        self.add_create_block("brick")
        self.add_create_block("switch")

        self.add_create_block("floaty")
        self.add_create_block("mushroom")

        self.add_create_block("coin_item")
        self.add_create_block("star")

        self.editing_level_label = tk.Label(self.mapeditor_level, text = level_to_edit)
        self.editing_level_label.pack(side = tk.LEFT, expand = True)


        save_button = tk.Button(self.mapeditor_level, text="Save & quit", command=self.save_edited_level, width=20)
        save_button.pack(side = tk.RIGHT)
        self.create_block_button["save_button"] = (save_button,None)

        delete_button = tk.Button(self.mapeditor_level, text="Delete", width="16", command = self.delete_callback)
        delete_button.pack(side = tk.RIGHT)
        self.create_block_button["delete_button"] = (delete_button,None)

        scroll_right_button = tk.Button(self.mapeditor_level, text=">>>", command = self.scroll_right)
        scroll_right_button.pack(side = tk.RIGHT)
        self.create_block_button["scroll_right_button"] = (scroll_right_button,None)

        scroll_left_button = tk.Button(self.mapeditor_level, text="<<<", command = self.scroll_left)
        scroll_left_button.pack(side = tk.RIGHT)
        self.create_block_button["scroll_left_button"] = (scroll_left_button,None)

        self._map_view.bind("<Button-1>", self.edit_block_on_map)
        self.block_picked = None
        self.map_editor_view_center = 0

    def scroll_left(self):
        if self.map_editor_view_center >= 16*BLOCK_SIZE:
            self.map_editor_view_center -= 16*BLOCK_SIZE
            self.scroll_editing_map()
    def scroll_right(self):
        if self.map_editor_view_center <= self._map.get_pixel_size()[0] - 16*BLOCK_SIZE:
            self.map_editor_view_center += 16*BLOCK_SIZE
            self.scroll_editing_map()

    def scroll_editing_map(self):
        half_screen = self._master.winfo_width() / 2
        world_size = self._map.get_pixel_size()[0] - half_screen
        # Left side
        if self.map_editor_view_center <= half_screen:
            self._map_view.set_offset((0, 0))

        # Between left and right sides
        elif half_screen <= self.map_editor_view_center <= world_size:
            self._map_view.set_offset((half_screen - self.map_editor_view_center, 0))

        # Right side
        elif self.map_editor_view_center >= world_size:
            self._map_view.set_offset((half_screen - world_size, 0))
        self.redraw_map_editor()

    def edit_block_on_map(self, event):
        #Add chosen block to map upon clicking if a create block is picked before.
        self.map_edited = True
        editing_x_position = int((event.x - self._map_view.get_offset()[0]) // BLOCK_SIZE)
        editing_y_position = event.y // BLOCK_SIZE

        if self.block_picked == "tunnel":
            sign = "="
        if self.block_picked == "flag_block":
            sign = "I"
        if self.block_picked == "coin":
            sign = "$"
        if self.block_picked == "brick":
            sign = "#"
        if self.block_picked == "switch":
            sign = "S"
        if self.block_picked == "floaty":
            sign = "&"
        if self.block_picked == "mushroom":
            sign = "@"
        if self.block_picked == "coin_item":
            sign = "C"
        if self.block_picked == "star":
            sign = "*"
        if self.block_picked == "delete":
            sign = " "
        if self.block_picked == None:
            self.map_edited = False

        if not self.map_edited:
            pass
        else:

            with open(self.editing_level_name, "r") as unmodified_file:
                unmodified_content = unmodified_file.readlines()
            modified_file = open(self.editing_level_name+".tmp", "w+")

            max_width = len(max(unmodified_content))
            for y, line in enumerate(unmodified_content):
                fill = max_width - len(line)
                line_str = line.rstrip("\n") + fill * " " + "\n"
                if y == editing_y_position:
                    line_list = list(line_str)
                    line_list[editing_x_position] = sign
                    line_str = "".join(line_list)
                modified_file.write(line_str)
            unmodified_file.close()
            modified_file.close()

            try:
                os.rename(self.editing_level_name+".tmp", self.editing_level_name)
            except WindowsError:
                os.remove(self.editing_level_name)
                os.rename(self.editing_level_name+".tmp", self.editing_level_name)


            self._map = load_world(self._map_builder, self.editing_level_name)
            self.redraw_map_editor()

    def redraw_map_editor(self):
        self._map_builder.clear()
        self._map_view.delete(tk.ALL)
        self._map_view.draw_entities(self._map.get_all_things())

    def add_create_block(self, block_name):
        #Add create buttons of block with block image to the bottom of the map
        button_callback = self.create_callback(block_name)
        button_image = tk.PhotoImage(file="images/" + block_name + ".png")

        button = tk.Button(self.mapeditor_level, width="16", height="16", image=button_image, command = button_callback)
        button.pack(side = tk.LEFT)
        #Save button_image to avoid garbage collection
        self.create_block_button[block_name] = (button, button_image)

    def delete_callback(self):
        #Delete button callback
        self.mapeditor_level.config(cursor="X_cursor")
        self.block_picked = "delete"

    def create_callback(self, block_name):
        #Create call back function dynamiclly for every add block button in the map editor
        def callback():
            self.block_picked = block_name
            self.mapeditor_level.config(cursor="plus")
            print(self.block_picked)
        callback.__name__ = block_name +"_create_button_call_back"
        return callback

    def save_edited_level(self):
        #Save edited level and continue previous game
        self.mapeditor_level.destroy()
        self.map_edited = False
        self.resume()

    def edit_level_closing(self):
        #Deal with editor closing, if level edited and not saved ask if save.
        if self.map_edited:
            if messagebox.askokcancel("Edited level not saving!", "Leave without saving?"):
                self.mapeditor_level.destroy()
                self.resume()
            else:
                pass
        else:
            self.mapeditor_level.destroy()
            self.resume()

    def pause(self):
        #pause the game by stop step()
        self._pause = True

    def resume(self):
        #resume the game by cotinue step()
        self._pause = False

    def write_highscore(self):
        #Write high score if reach next level
        self.pause()
        self.write_highscore_top_level = tk.Toplevel()
        self.write_highscore_top_level.title("Enter ur name for highscore!")
        label = tk.Label(self.write_highscore_top_level, text='Your name:')
        label.pack(side=tk.LEFT)
        self.highscore_entry = tk.Entry(self.write_highscore_top_level, width=40)
        self.highscore_entry.pack(side=tk.LEFT)

        enter = tk.Button(self.write_highscore_top_level, text="Enter", command=self.enter)
        enter.pack(side=tk.LEFT)

        self.write_highscore_top_level.bind('<Return>', self.enter)
        self.write_highscore_top_level.protocol("WM_DELETE_WINDOW", self.write_highscore_closing)

    def write_highscore_closing(self):
        #If high score is not saved, and close the high score record window, ask wether save.
        if messagebox.askokcancel("Record not saving!", "Leave without saving?"):
            self.resume()
            self.write_highscore_top_level.destroy()
        else:
            self.write_highscore_top_level.destroy()
            self.write_highscore()

    def enter(self, event=None):
        #Record the high score is the enter button is pressed
        highscore = open(self._last_level + "high_score.txt", "a+")
        name = self.highscore_entry.get()
        score = str(self._player.get_score())
        record = name + ',' + score + '\n'
        self.write_highscore_top_level.destroy()
        highscore.write(record)
        self.resume()

    def read_highscore(self):
        #Read high score i
        high_score_list = []
        text_to_show = 'rank      name      score\n'
        num_of_record = 0
        try:
            highscore = open(self._level + "high_score.txt", "r+")
        except IOError:
            highscore = []
        for line in highscore:
            high_score_list.append(line.rstrip().split(","))
            num_of_record += 1
        high_score_list.sort(key=lambda x: int(x[1]), reverse= True)
        if num_of_record >= 10:
            for i in range(0,10):
                text_to_show += (str(i+1)+'       ' + high_score_list[i][0] + '       ' + high_score_list[i][1] + '\n')
        else:
            for i in range(0, num_of_record):
                text_to_show += (str(i+1)+'       ' + high_score_list[i][0] + '       ' + high_score_list[i][1] + '\n')
        self.read_highscore_top_level = tk.Toplevel()
        self.read_highscore_top_level.title("Leaderboard")

        record =  tk.Text(self.read_highscore_top_level, height=10, width=30)
        record.insert(tk.END, text_to_show)
        record.pack(side=tk.LEFT)
        self.pause()
        self.read_highscore_top_level.protocol("WM_DELETE_WINDOW", self.read_highscore_closing)

    def read_highscore_closing(self):
        self.resume()
        self.read_highscore_top_level.destroy()

    def takeScore(self, high_score_list):
        return int(high_score_list[1])

    def reset_world(self, new_level="level1.txt"):

        starting_x = BLOCK_SIZE
        starting_y = BLOCK_SIZE
        if "x" in self.configuration:
            starting_x = self.configuration["x"]
        if "y" in self.configuration:
            starting_y = self.configuration["y"]

        self._builder.clear()
        self._world = load_world(self._builder, new_level)
        self._setup_collision_handlers()
        self._world.add_player(self._player, starting_x, starting_y)
        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
        try:
            self._view.destroy()
        except:
            pass
        self._view = GameView(self._master, size, self._renderer)
        self._view.pack(side = tk.TOP)


    def bind(self):
        """Bind all the keyboard events to their event handlers."""
        self._master.bind("<Key>", self._move_event)

    def _move_event(self, event):
        if event.keysym == 'Right' or event.keysym == 'r'or event.keysym == 'd':
            vx = MARIO_VEL['vx']
            vy = self._player.get_velocity()[1]
            self._move(vx, vy)
            print('r')
        elif event.keysym == 'Left' or event.keysym == 'l' or event.keysym == 'a':
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

    def load_level(self, filename = None, resetplayer = True):
        if not filename:
            self.pause()
            level_name = filedialog.askopenfilename()
            if level_name == None:
                self.resume()
            elif not self._level.endswith('.txt'):
                messagebox.showinfo("File error","A level file should end with .txt")
                self.load_level()
            else:
                self._level = level_name
                self.reset_level(resetplayer)
                self.resume()

        elif filename == "END":
            messagebox.showinfo("CONGRATULATIONS", "You won the game!")
            self.exit()
        else:
            self._last_level = self._level
            try :
                open(filename)
                self._level = filename
                self.reset_level(resetplayer)
            except:
                messagebox.showinfo("Error", "Can't find next level file")
                self.exit()

    def reset_level(self, resetplayer = True):
        if resetplayer:
            self._player = Player(name = self.character, max_health=self.configuration["health"])
        self.reset_world(self._level)

    def dead_ask_reset(self):
        if self._player.is_dead():
             reply = messagebox.askquestion(type=messagebox.YESNO,
                                            title="You are dead!",
                                            message="Would you like to restart the level?")
             if reply == messagebox.YES :
                 self.reset_level()
             elif reply == messagebox.NO :
                 self.exit()

    def exit(self):
        self._exit = True

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


        if self._pause == True:
            pass
        else:
            data = (self._world, self._player)
            self._world.step(data)
            self._status_bar.update_status(self._player)
            self.invisble_step()
            self.scroll()
            self.redraw()
            self.dead_ask_reset()


        if self._exit == True:
            exit(0)

        self._master.after(10, self.step)

    def _move(self, dx, dy):
        self._player.set_velocity([dx,dy])

    def _jump(self):
        vx,vy = self._player.get_velocity()
        if(vy == 0):
            vy = MARIO_VEL['vy']
        self._player.set_velocity([vx, vy])

    def _duck(self):
        if self._player.is_on_tunnel():
            self._player.get_tunnel().triger(self)
            self._player.off_tunnel()

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
        if block not in self.invisible_list:
            if block.get_id() == 'switch' :
                if block.is_pressed():
                    return False
            if mob.get_id() == "fireball":
                if block.get_id() == "brick":
                    self._world.remove_block(block)
                self._world.remove_mob(mob)
            if mob.get_id() == "mushroom":
                mob.collide(block)
            return True
        else:
            return False

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
        """
        Callback to handle with player collide with a block
        Args:
            player(Player): the player in the game
            block(Block): the block player collide with
            data(dict):data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter)

        Returns:False if the item is in invisible list or the seitch pressed, otherwise, True

        """
        if block not in self.invisible_list:
            if block.get_id() == "flag":
                block.on_hit(self, self._player)
            elif block.get_id() == 'tunnel':
                block.on_hit(player)
            elif block.get_id() == 'switch':
                block.on_hit(arbiter, (self._world, player))
                if block.is_pressed():
                    in_range_list = self._world.get_things_in_range(block.get_position()[0],block.get_position()[1], block.get_invisible_radius())
                    for thing in in_range_list:
                        if isinstance(thing, Block) :
                            if thing.get_id()== "brick":
                                self._world.remove_block(thing)
                                #invisible time = 1000 * 10ms
                                self.invisible_list.append([thing, 1000])
                    return False
            else:
                block.on_hit(arbiter, (self._world, player))
            return True
        else:
            return False
        
    def invisble_step(self):
        """
        Reduce the invisible time for each invisible items in the invisible list when step function is run
        """
        for invisible in self.invisible_list:
            invisible[1] -= 1
            invisible_block, invisible_time = invisible
            if invisible_time <= 0:
                self._world.add_block(invisible_block, invisible_block.get_position()[0], invisible_block.get_position()[1])
                self.invisible_list.remove(invisible)

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        """
        Callback to handle with player collide with a mob
        Args:
            player(Player): the player in the game
            mob(Mob): the mob player collide with
            data(dict):data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter)

        Returns:bool True
        """
        mob.on_hit(arbiter, (self._world, player))
        if player.is_invincible():
            self._world.remove_mob(mob)
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        """
        Callback to handle with player seperate with a block
        Args:
            player(Player): the player in the game
            block(Block): the block player collide with
            data(dict):data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter)

        Returns:bool True
        """
        if(block.get_id() == 'tunnel'):
            player.off_tunnel()
        return True

class StatusBar(tk.Frame):
    """
        A class to create status bar in the view
    """

    BARHEIGHT = 20
    def __init__(self, master, player):
        """
        Construct a statusbar consisting of health bar and score bar in the game view
        Args:
            master (tk.Tk | tk.Toplevel | tk.Frame): The tkinter master widget
            player(Player): the player in the game
        """

        self._score = player.get_score()
        self._width = MAX_WINDOW_SIZE[0]

        self._score_label = tk.Label(master, text="Score: {0}".format(self._score))
        self._score_label.pack(side =tk.BOTTOM)
        self.canvas = tk.Canvas(master, width = self._width, height = self.BARHEIGHT, bg ='black',  highlightthickness = 0, borderwidth = 0)
        self.display_health(player)
        self.canvas.pack(side =tk.BOTTOM)

    def display_health(self, player):

        """
        Draw the health bar in the game
        Args:
            player(Playe): The player in the game
        """

        health_percent =  player.get_health() / player.get_max_health()
        if health_percent > 0.5:
            color = 'green'
        elif health_percent > 0.25:
            color = 'orange'
        else:
            color = 'red'

        if player.is_invincible():
            color = 'yellow'
        self.canvas.create_rectangle(0, 0, health_percent * self._width, self.BARHEIGHT , fill= color)

    def update_status(self, player):
        """
        The updating of the status bar in every step
        Args:
            player(Player): The player in the game

        """
        self.canvas.delete("all")
        self.display_health(player)
        self._score = player.get_score()
        self._score_label.config(text = "Score: {0}".format(self._score))

class Mushroom(Mob):
    """
    A mushroom class in tbe game is a kind of mob player lose health when collide with mushroom
    """
    _id = "mushroom"

    def __init__(self):
        """
            Init from supercalss, Mob, with size weight and temp
        """
        super().__init__(self._id, size=(16, 16), weight=300, tempo=100)

    def on_hit(self, event: pymunk.Arbiter, data):
        """
        Deal with player colliding with mushroom
        If player land on the top of mushroom mob, mushroom will be removed.
        If player come from left or right, player's health shoould be reduced by 1,
         and player should be bounced back.
        Args:
            event:
            data:

        """
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
            player.set_velocity([player_vx, 400])
            world.remove_mob(self)

    def collide(self, entity):
        """
        Deal with mushroom turn to opposite when collide with other things
        Args:
            entity: the entity mushroom collide with.

        """
        if get_collision_direction(entity, self) == "R" or \
                get_collision_direction(entity, self) == "L":
            self.set_tempo(-self.get_tempo())

class BounceBlock(Block):

    """
        A bounce block class in the game, player would bounce when step on it
    """

    _id = "bounce_block"
    def on_hit(self, event, data):
        """
        When player land on the top of a bounce block, he will be bounced up.
        """
        world, player = data
        if get_collision_direction(player, self) == "A":
            vx = data[1].get_velocity()[0]
            vy = -300
            data[1].set_velocity([vx, vy])

class Star(DroppedItem):
    """
    Player would be vincible after picking up a star.
    """
    _id = "star"

    def collect(self, player: Player):
        """
        Set player to invincible when star is collected.
        Args:
            player:
        """
        player.invincible()

class Goal(Block):
    """
    A class for the goal in the game.
    """
    _id = "goal"
    _cell_size = (1, 1)

    def triger(self, app, trigger_id = None):
        """
        When a goal is activated, the game should load another level and record the highscore for current level.
        Args:
            app:
            trigger_id:
        """
        now_level_line = 0
        for line_content in app.config_file_content:
            if line_content.find('==' + app._level + '==')!= -1:
                break
            
            now_level_line += 1
        if not trigger_id:
            trigger_id = self._id
        found = False
        for line_content in app.config_file_content[now_level_line:]:
            if app.find_in_line_and_config(line_content, trigger_id, str):
                found = True
                break
        if found == False:
            app.write_highscore()
            messagebox.showinfo("Configure Error","Can't find next level")
            app.exit()
        else:
            app.write_highscore()
            app.load_level(filename = app.configuration[trigger_id], resetplayer=False)

class Flag(Goal):
    """
    Player go to next level once they collide with a flag and would get bounce health if they land on top of it.
    """
    _id = "flag"
    _cell_size = GOAL_SIZES.get(_id)

    def on_hit(self, app, player):
        """
        callback when user hit a flag
        """
        if get_collision_direction(player, self) == "A":
            player.change_health(1)
        super().triger(app,"goal")

class Tunnel(Goal):
    """
    When player pressed 'DOWN' on top of the tunnel, they will go to bounce level
    """
    _id = "tunnel"
    _cell_size = GOAL_SIZES.get(_id)

    def on_hit(self,player):
        """
        When player hit with a tunnel , check the direction.
        Args:
            player:
        """
        if get_collision_direction(player, self) == "A":
            player.on_tunnel(self)

class Switch(Block):
    """
       When player land on top of the switch ,the block with in arange to the switch will disappear.
    """
    _id = "switch"
    _invisible_radius = 64

    def __init__(self):
        """
        Construct a switch block and set the it to unpressed by signing pressed_time to 0
        """
        super().__init__()
        self.pressed_time = 0

    def on_hit(self, event, data):
        """
        callback when switch is hit by user
        """
        world, player = data

        if get_collision_direction(player, self) == "A":
            if not self.is_pressed():
                self.set_pressed_time()

    def set_pressed_time(self, time = 1000):
        """
        Set the switch status to pressed
        Args:
            time: set the switch pressed time to 10s
        """
        self.pressed_time = time

    def step(self, time_delta, game_data):
        """
            Reduce pressed time by 1 count for the pressed time
        """
        if self.is_pressed():
            self.pressed_time -= 1

    def is_pressed(self):
        """
        Return if the switch is pressed
        Returns: int the left presssed time for the switch
        """
        return self.pressed_time > 0

    def get_invisible_radius(self):
        """
        return the radius for blocking
        Returns: int the blocking radius

        """
        return self._invisible_radius

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

    @ViewRenderer.draw.register(Switch)
    def _draw_switch(self, instance: Switch, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_pressed():
            image = self.load_image("switch_pressed")
        else:
            image = self.load_image("switch")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]


class SpriteSheetLoader():
    """
    A class to read  pictures from the spritesheet.
    """
    def __init__(self, sheet_name, region, pic_name):
        """
        Cut pictures from the spritesheet and save it into _image directory
        Args:
            sheet_name(str):the sheet to cut pics from
            region(tuple(int,int,int,int)): the starting and ending x,y of the cutting region
            pic_name: the name of the image get from cutting

        """
        im = Image.open(sheet_name)
        im = Image.open("spritesheets/characters.png")
        pic = im.crop(region)
        pic.save("_images/trail.png")



def main():
    root = tk.Tk()
    app = MarioApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
