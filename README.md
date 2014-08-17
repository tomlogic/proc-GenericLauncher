proc-GenericLauncher
====================

This is a Python-based front-end game launcher for a P-ROC enabled pinball
machine.  Using it shouldn't require any modifications to GameLauncher.py,
just the creation of a Loader.yaml file based on one of the provided examples.

The DemoMan example demonstrates some recent additions for PinMAME-based
games.  The launcher now supports multiple configurations (NVRAM files) for
each ROM file, and will cycle through those options.  The DemoMan example
shows options for 3-ball, 5-ball and "tournament mode".

The launcher can also read the Grand Champion initials and score from the
NVRAM file to display with the rest of the game description.  When launching
a given configuration, it makes use of the configuration's NVRAM file.

This version of the launcher has not been tested on Windows.  It should work
after updating Loader.yaml to use Windows paths.

Discussion of this project takes place in [this topic][1] on the
PinballControllers Forum.

[1]: http://www.pinballcontrollers.com/forum/index.php?topic=1277.0
