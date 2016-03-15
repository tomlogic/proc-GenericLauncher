#  GameLauncher
#
#   An all-in-one front-end for PyProcGame to launch games from
#   your P-ROC enabled Williams pinball machine.  Use the  yaml
#   to define games to launch pinmame (Williams, FreeWPC), procgame 
#   or PyProcGame games
#
# Authors:
#   Tom Collins (tomlogic)
#   Michael Ocean (mocean)
#   Based on the F-14 Loader by Mark (Snux) which was based on
#   Original code from Jim (myPinballs) and Koen (DutchPinball)
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
import shutil
import sys
import locale
import yaml

# Loader specific file is required; and expected to live in the same
# directory.  Gross to load it globally?  Sure.
loader_config_path = 'Loader.yaml'
loaderconfig = None

def format_score(number):
	if sys.version_info >= (2,7,0):
		return '{0:,}'.format(number)
	
	s = '%d' % number
	groups = []
	while s and s[-1].isdigit():
		groups.append(s[-3:])
		s = s[:-3]
	return s + ','.join(reversed(groups))

def getnested(node, key):
	""" Helper function to access a deep element of a dict/list using dot notation. """
	keys = key.split('.')
	try:
		for key in keys:
			if isinstance(node, list):
				key = int(key)
			node = node[key]
		return node
	except TypeError:
		pass

class Loader(game.Mode):
    """
    A Mode derived class to actually deal with prompting for a player's
    game selection and actually loading the game
    """

    def __init__(self, game, priority):
        super(Loader, self).__init__(game, priority)

        global loaderconfig
        self.game_index = 0 # number of selected game (indexed from 0)
        self.config_index = 0    # number of selected game's configuration
        self.configs = None
        self.selected_config = None
        self.selected_game = None
        
        # pull out some config values that we know we'll need up
        # front.  Should any of these fail, it's OK to fail loudly
        self.title = loaderconfig['title']
        self.instructions_line_1 = loaderconfig['instructions_line_1']
        self.instructions_line_2 = loaderconfig['instructions_line_2']
        
        self.games = loaderconfig['games']
        self.pinmame_path =  loaderconfig['pinmame']['path']
        self.pinmame_cmd = loaderconfig['pinmame']['cmd']
        self.pinmame_nvram = loaderconfig['pinmame']['nvram']
        self.python_path =  loaderconfig['python']['cmdpath']

        # extra args for pinmame are totally optional
        self.pinmame_extra_args = ""
        if loaderconfig['pinmame'].has_key('extra_args'):
            self.pinmame_extra_args = loaderconfig['pinmame']['extra_args']

        # print(self.games)

        self.reset()

    def reset(self):
        # if changing this font, adjust the row as necessary to avoid clipping top of title
        self.title_layer = dmd.TextLayer(64, -2, font_named('Font_CC_12px_az.dmd'), "center", opaque=False)
        font = font_named("04B-03-7px.dmd")
        self.text1_layer = dmd.TextLayer(64, 0, font, "center", opaque=False)
        self.text2_layer = dmd.TextLayer(64, 8, font, "center", opaque=False)
        self.text3_layer = dmd.TextLayer(64, 16, font, "center", opaque=False)
        self.text4_layer = dmd.TextLayer(64, 24, font, "center", opaque=False)
        self.layer = dmd.GroupedLayer(128, 32, [self.text4_layer, self.text3_layer,
            self.text2_layer, self.text1_layer, self.title_layer])

    def mode_started(self):
        self.show_title()
        self.delay(name='gi_dim', event_type=None, delay=1.0, handler=self.gi_dim)

    def mode_tick(self):
        pass

    # Return a string with the Grand Champion initials and score for the
    # selected configuration of the selected game.
    def load_gc(self):
        gc = ''  # default to not show anything
        if self.selected_game.has_key('gc'):
            gcdict = self.selected_game['gc']
            score_file = None
            if self.selected_config.has_key('fileprefix'):
                score_file = self.selected_game['gamepath'] + self.selected_config['fileprefix'] \
                    + '-scores.yaml'
            elif self.selected_game.has_key('scores'):
                score_file = self.selected_game['gamepath'] + self.selected_game['scores']
            if score_file is not None:
                try:
                    yamlfile = open(score_file, 'r')
                    scores = yaml.load(yamlfile)
                    initials = getnested(scores, gcdict['initials'])
                    score = int(getnested(scores, gcdict['score']))
                    gc = 'GC: ' + initials + ' ' + format_score(score)
                except Exception:
                    # ignore exceptions (like when nvram file doesn't exist yet)
                    pass
            else:
                if self.selected_config.has_key('filename'):
                    basename = self.selected_config['filename']
                else:
                    basename = self.selected_game['ROM']
                
                # load the contents of the NVRAM file into a binary array
                try:
                    nvfile = open(self.pinmame_nvram + basename + '.nv', 'rb')
                    nvram = nvfile.read(32768)
                    nvfile.close()
                    
                    initials = ''
                    # read three characters with the champ's initials from the NVRAM
                    if gcdict.has_key('initials'):
                        offset = gcdict['initials']
                        initials = ' ' + nvram[offset:offset + 3]
                        gc = 'GC:' + initials      # show initials even if we don't know the score
                    
                    if gcdict.has_key('score'):
                        score = 0
                        offset = gcdict['score']
                        if gcdict.has_key('bcd_bytes'):
                            # convert the BCD-encoded bytes to an integer
                            for b in nvram[offset:offset + gcdict['bcd_bytes']]:
                                score = score * 100 + 10 * (ord(b) >> 4) + (ord(b) & 0x0F)
                    gc = 'GC:' + initials + ' ' + format_score(score)
                except Exception:
                    # ignore exceptions (like when nvram file doesn't exist yet)
                    pass
            
        return gc
        
    def show_title(self):
        self.title_layer.set_text(self.title)
        self.text1_layer.set_text('')
        self.text2_layer.set_text('')
        self.text3_layer.set_text(self.instructions_line_1)
        self.text4_layer.set_text(self.instructions_line_2)
        self.selected_game = None
        
    def gi_enable(self, dim=False):
        global loaderconfig
        
        if loaderconfig.has_key('gi_enable'):
            for lamp in loaderconfig['gi_enable']:
                if dim:
                    self.game.lamps[lamp].patter(on_time=1, off_time=2)
                else:
                    self.game.lamps[lamp].enable()
                    
        if loaderconfig.has_key('lampshow'):
            if dim:
                self.game.lampctrl.stop_show()
            else:
                if not self.game.lampctrl.show_playing:
                    self.game.lampctrl.register_show('lampshow', loaderconfig['lampshow'])
                    self.game.lampctrl.play_show('lampshow', repeat=True)
            
        if not dim:
            self.cancel_delayed('gi_dim')
            self.delay(name='gi_dim', event_type=None, delay=60.0, handler=self.gi_dim)
        
    def gi_dim(self):
        self.gi_enable(dim=True)
        
    def show_next_game(self,direction=0):
        self.gi_enable(dim=False)
        if self.selected_game is None:
            # from title, go to either 0 (first) or -1 (last) game/config
            self.game_index = self.config_index = 0 if direction > 0 else -1
            if self.game.lamps.has_key('startButton'):
                self.game.lamps.startButton.schedule(schedule=0xff00ff00, cycle_seconds=0, now=False)
        else:
            self.config_index += direction
        
            # If the user goes "left" of the first config, roll to the last
            # config of the previous game
            if self.config_index == -1:
                self.game_index -= 1
                # note that we need to load the configs for this new game_index
                # before we can set config_index to the last configuration
                
            # If we have gone past the last config, roll over to the first
            # configuration of the next game.
            elif self.config_index == len(self.configs):
                self.game_index += 1
                self.config_index = 0
        
        # use the modulus operator to wrap-around game_index
        self.game_index = self.game_index % len(self.games)
        
        self.selected_game = self.games[self.game_index]
        if self.selected_game.has_key('configuration'):
            self.configs = self.selected_game['configuration']
        else:
            self.configs = [{'description': 'default configuration'}]
        
        if self.config_index == -1:
            # We can now select the last configuration of the newly-selected game.
            self.config_index = len(self.configs) - 1
        
        self.selected_config = self.configs[self.config_index]
        
        # Update the DMD screen to describe the current game/config option.
        self.title_layer.set_text('')
        self.text1_layer.set_text(self.selected_game['line1'])
        self.text2_layer.set_text(self.selected_game['line2'])
        self.text3_layer.set_text(self.selected_config['description'])
        self.text4_layer.set_text(self.load_gc())

    def sw_startButton_active(self, sw):
        global loaderconfig
        
        # Ignore start button if we're on the title/startup screen.
        if self.selected_game is None:
            return
            
        if self.selected_game.has_key('ROM'):
            # args for launching PinMAME directly
            args = self.selected_game['ROM'] + " -p-roc " \
                + loaderconfig['machine_config_file'] + " " + self.pinmame_extra_args
                
            # args for launching PinMAME via a shell script (runpinmame) or batch file
#            args = self.selected_game['ROM'] + " " + loaderconfig['machine_config_file']
            
            pinmame_nvfile = self.pinmame_nvram + self.selected_game['ROM'] + '.nv'
            config_nvfile = None
            if self.selected_config.has_key('filename'):
                config_nvfile = self.pinmame_nvram + self.selected_config['filename'] + '.nv'
                if os.path.isfile(config_nvfile):
                    # copy configuration's nvram file to PinMAME's version of the file 
                    print 'Copying ' + config_nvfile + ' to ' + pinmame_nvfile
                    shutil.copyfile(config_nvfile, pinmame_nvfile)
                        
            # actually run PinMAME
            self.launch_ext(self.pinmame_cmd, args, self.pinmame_path)
                
            # upon return, copy the modified nvram file back (if necessary)
            if config_nvfile is not None:
                # copy PinMAME's version of the file back to the configuration's file
                print 'Copying ' + pinmame_nvfile + ' back to ' + config_nvfile
                shutil.copyfile(pinmame_nvfile, config_nvfile)
        else:
            config_settings = None
            config_scores = None
            settings_yaml = None
            scores_yaml = None
            
            # copy configuration's settings and scores YAML files to the game's path
            try:
                settings_yaml = self.selected_game['gamepath'] + self.selected_game['settings']
                config_settings = self.selected_game['gamepath'] + self.selected_config['fileprefix'] \
                    + '-settings.yaml'
                if os.path.isfile(config_settings):
                    print 'Copying ' + config_settings + ' to ' + settings_yaml
                    shutil.copyfile(config_settings, settings_yaml)
            except Exception as detail:
                # ignore exceptions (like when there aren't files to copy)
                print "failed to copy config settings: ", detail
            try:
                scores_yaml = self.selected_game['gamepath'] + self.selected_game['scores']
                config_scores = self.selected_game['gamepath'] + self.selected_config['fileprefix'] \
                    + '-scores.yaml'
                if os.path.isfile(config_scores):
                    print 'Copying ' + config_scores + ' to ' + scores_yaml
                    shutil.copyfile(config_scores, scores_yaml)
            except Exception as detail:
                # ignore exceptions (like when there aren't files to copy)
                print "failed to copy config scores: ", detail
            
            self.launch_ext(self.python_path,self.selected_game['gamefile'],self.selected_game['gamepath'])
            # self.launch_python(self.selected_game['gamefile'],self.selected_game['gamepath'])
                
            # upon return, copy the modified settings and scores files back (if necessary)
            try:
                if config_settings is not None and settings_yaml is not None:
                    print 'Copying ' + settings_yaml + ' back to ' + config_settings
                    shutil.copyfile(settings_yaml, config_settings)
            except Exception as detail:
                # ignore exceptions (like when there aren't files to copy)
                print "failed to save config settings: ", detail
            try:
                if config_scores is not None and scores_yaml is not None:
                    print 'Copying ' + scores_yaml + ' back to ' + config_scores
                    shutil.copyfile(scores_yaml, config_scores)
            except Exception as detail:
                # ignore exceptions (like when there aren't files to copy)
                print "failed to save config scores: ", detail

    def sw_flipperLwL_active(self, sw):
        self.show_next_game(direction=-1)

    def sw_flipperLwR_active(self, sw):
        self.show_next_game(direction=1)

    def launch_ext(self, cmd, args, path):
        """
        launch a either a pinmame based game or a PyProc-based game by 
        running the executable and corresponding arguments. In the case
        of Python-based games, this /could/ be done by launching the game class,
        but for my needs, I want to be able to run multiple games
        that are different, but have the same module names (e.g., many
        games will have a BaseGameMode but that mode will be different)
        """
        self.cancel_delayed('gi_dim')
        self.game.lampctrl.stop_show()
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
        self.game.enable_flippers(False)
        self.game.dmd.frame_handlers.append(self.game.proc.dmd_draw)
        self.game.dmd.frame_handlers.append(self.game.set_last_frame)

#########################################
## 
#########################################

class Game(game.BasicGame):
    """ the 'game' portion of the Loader """
    def __init__(self, machine_type):
        super(Game, self).__init__(machine_type)
        self.lampctrl = lamps.LampController(self)

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
        if self.coils.has_key('flipperEnable'):
            enable = True
            self.coils.flipperEnable.pulse(0)
        super(game.BasicGame, self).enable_flippers(enable)

    def reset(self):
        # Reset the entire game framework
        super(Game, self).reset()

        # Add the basic modes to the mode queue
        self.modes.add(self.loader)

        # Make sure flippers are off
        self.enable_flippers(False)

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
            game.run_loop()
            # Reset mode & restart P-ROC / pyprocgame
            game.loader.mode_started()
            game.loader.restart_proc()
    finally:
        del game

if __name__ == '__main__': main()
