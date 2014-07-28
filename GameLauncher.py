#  GameLauncher
#
#   An all-in-one front-end for PyProcGame to launch games from
#   your P-ROC enabled Williams pinball machine.  Use the  yaml
#   to define games to launch pinmame (Williams, FreeWPC), procgame 
#   or PyProcGame games
#
# Michael Ocean (mocean)
# Based on the F-14 Loader by Mark (Snux) which was based on
# Original code from Jim (myPinballs) and Koen (DutchPinball)
#
# This is intended to be a one-size-fits-all launcher; in theory all
#   you need to supply is a Loader.yaml and this launcher will work.  
#   Everything is smashed into this single file (which may
#   not be terribly 'Pythonic', but that's not the point...)
#   Honestly, Mark Jim and Koen did the hard part by writing the original
#   launching code (starting and stopping the P-ROC).  I haven't done much
#   other than moving everything into one file and moving all of the 
#   would-be options out of the code and into a yaml file.
#
#   Clearly none of this would make any sense without the brilliant work
#   of Gerry Stellenberg and Adam Premble
#
# This is a work in progress.  
# Please report issues on the PinballControllers forum.
#

from procgame import *
from procgame.dmd import font_named
import os
import sys
import locale
import yaml

sys.path.append(sys.path[0]+'/../..') # Set the path so we can find procgame.  We are assuming (stupidly?) that the first member is our directory.

# Loader specific file is required; and expected to live in the same
# directory.  Gross to load it globally?  Sure.
loader_config_path = 'Loader.yaml'
loaderconfig = None

class Loader(game.Mode):
    """
    A Mode derived class to actually deal with prompting for a player's
    game selection and actually loading the game
    """

    def __init__(self, game, priority):
        super(Loader, self).__init__(game, priority)

        global loaderconfig
        self.selection=0 # number of selected game (indexed from 0)
        
        # pull out some config values that we know we'll need up
        # front.  Should any of these fail, it's OK to fail loudly
        self.instructions_line_1 = loaderconfig['instructions_line_1']
        self.instructions_line_2 = loaderconfig['instructions_line_2']
        
        self.games = loaderconfig['games']
        self.pinmame_path =  loaderconfig['pinmame']['path']
        self.pinmame_cmd = loaderconfig['pinmame']['cmd']
        self.python_path =  loaderconfig['python']['cmdpath']

        # extra args for pinmame are totally optional
        self.pinmame_extra_args = ""
        if(loaderconfig['pinmame'].has_key('extra_args')):
            self.extra_args = loaderconfig['pinmame']['extra_args']

        # print(self.games)

        self.reset()

    def reset(self):
        self.text1a_layer = dmd.TextLayer(64, 1, font_named("04B-03-7px.dmd"), "center", opaque=False).set_text(self.instructions_line_1)
        self.text1b_layer = dmd.TextLayer(64, 9, font_named("04B-03-7px.dmd"), "center", opaque=False).set_text(self.instructions_line_2)
        self.text2_layer = dmd.TextLayer(64, 17, font_named("04B-03-7px.dmd"), "center", opaque=False)
        self.text3_layer = dmd.TextLayer(64, 25, font_named("04B-03-7px.dmd"), "center", opaque=False)
        self.layer = dmd.GroupedLayer(128, 32, [self.text3_layer,self.text2_layer, self.text1a_layer, self.text1b_layer])#set clear time

    def mode_started(self):
        self.show_next_game()

    def mode_tick(self):
        pass

    def show_next_game(self,direction=0):            
        self.selection+=direction
        # use the modulus operator to wrap-around selection
        self.selection = self.selection % len(self.games)
        
        self.text2_layer.set_text(self.games[self.selection]['line1'],blink_frames=20)
        self.text3_layer.set_text(self.games[self.selection]['line2'])

    def sw_startButton_active(self, sw):
        global loaderconfig
        if(self.games[self.selection].has_key('ROM')):
            # print('game is ROM')
            args = self.games[self.selection]['ROM'] + \
                " -p-roc "+loaderconfig['machine_config_file']+" "+self.pinmame_extra_args
            self.launch_ext(self.pinmame_cmd, args, self.pinmame_path)
        else:           
            # print('game is Python')
            self.launch_ext(self.python_path,self.games[self.selection]['gamefile'],self.games[self.selection]['gamepath'])
            # self.launch_python(self.games[self.selection]['gamefile'],self.games[self.selection]['gamepath'])

    def sw_flipperLwL_active(self, sw):
        self.show_next_game(direction=-1)

    def sw_flipperLwR_active(self, sw):
        self.show_next_game(direction=1)

    def launch_ext(self, cmd, args, path):
        """
        launch a either a pinmame based game or a PyProc-based game by 
        running the executable and corresponding arguments. In the classes
        of Python-based games, this /could/ be done by launching the game class,
        but for my needs, I want to be able to run multiple games
        that are different, but have the same module names (e.g., many
        games will have a BaseGameMode but that mode will be different)
        """
        self.stop_proc()

        os.chdir(path); 

        # Call an executable to take over from here, further execution of Python code is halted.
        print(cmd+" "+args)
        os.system(cmd+" "+args)

        # Pinmame/PyProcGame executable was:
        # - Quit by a delete on the keyboard
        # - Interupted by flipper buttons + start button combo
        # - died


    def get_class( self, kls, path_adj='/.' ):
        """Returns a class for the given fully qualified class name, *kls*.
        Source: http://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname

        this is left here if someone wants to try to find an elegant recursive
        reload solution for classes; otherwise launching two different PyProcGame
        based games that have module names in common will not work (will just use
        the previously loaded modules)
        """
        sys.path.append(sys.path[0]+path_adj)
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        reload(m)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

    def launch_python(self, gameclass, gamepath):
        """
        this is left here if someone wants to try to find an elegant recursive
        reload solution for classes; otherwise launching two different PyProcGame
        based games that have module names in common will not work (will just use
        the previously loaded modules)
        """
        self.stop_proc()
        print("launching [" + gameclass + "] from [" + gamepath + "]")
        
        klass = self.get_class(gameclass,gamepath)
        game = klass()
        # launch the game
        game.run_loop()
        
        # game exited so
        del game


    def stop_proc(self):
        self.game.end_run_loop()
        while len(self.game.dmd.frame_handlers) > 0:
            del self.game.dmd.frame_handlers[0]
        del self.game.proc

    def restart_proc(self):
        self.game.proc = self.game.create_pinproc()
        self.game.proc.reset(1)
        self.game.load_config(self.game.yamlpath)
        # On Sys11 games (with flipperEnable coil), we need to enable the
        # flippers to detect button presses via the coil EOS switches.
        self.game.enable_flippers(self.game.coils.has_key('flipperEnable'))
        self.game.dmd.frame_handlers.append(self.game.proc.dmd_draw)
        self.game.dmd.frame_handlers.append(self.game.set_last_frame)

#########################################
## 
#########################################

class Game(game.BasicGame):
    """ the 'game' portion of the Loader """
    def __init__(self, machine_type):
        super(Game, self).__init__(machine_type)

    def setup(self):
        """docstring for setup"""
        self.load_config(self.yamlpath)

        self.loader = Loader(self,2)
        # Instead of resetting everything here as well as when a user
        # initiated reset occurs, do everything in self.reset() and call it
        # now and during a user initiated reset.
        self.reset()

    def enable_flippers(self,enable):
        """ enables flippers on pre-fliptronics machines by checking for the
            presence of a coil with name flipperEnable which is mapped to the 
            flipper enable relay (G08)
        """
        super(game.BasicGame, self).enable_flippers(enable)
        if(self.coils.has_key('flipperEnable')):
            if enable:
                self.coils.flipperEnable.pulse(0)
            else:
                self.coils.flipperEnable.disable()

    def reset(self):
        # Reset the entire game framework
        super(Game, self).reset()

        # Add the basic modes to the mode queue
        self.modes.add(self.loader)

        # Make sure flippers are off, especially for user initiated resets.
        self.enable_flippers(enable=False)

def main():
    # actually load the Loader.yaml file
    print("Using Loader config at: %s "%(loader_config_path))
    global loaderconfig 
    loaderconfig = yaml.load(open(loader_config_path, 'r'))

    # find the appropriate machine specific yaml file from
    # Loader.yaml
    machine_config_file = loaderconfig['machine_config_file']

    config = yaml.load(open(machine_config_file, 'r'))
    print("Using machine config at: %s "%(machine_config_file))
    
    machine_type = config['PRGame']['machineType']
    config = 0
    game = None
    try:
        game = Game(machine_type)
        game.yamlpath = machine_config_file
        game.setup()
        while 1:
            if game.lamps.has_key('startButton'):
                game.lamps.startButton.schedule(schedule=0xff00ff00, cycle_seconds=0, now=False)
            game.run_loop()
            # Reset mode & restart P-ROC / pyprocgame
            game.loader.mode_started()
            game.loader.restart_proc()
    finally:
        del game

if __name__ == '__main__': main()
