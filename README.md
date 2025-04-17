What is this?
=============

Pippy allows the student to examine, execute, and modify simple Python programs.  In addition it is possible to write Python statements to play sounds, calculate  expressions, or make simple text based interactive games.

How to use?
===========

Pippy is part of the Sugar desktop.  Please refer to;

* [How to Get Sugar on sugarlabs.org](https://sugarlabs.org/),
* [How to use Sugar](https://help.sugarlabs.org/),
* [How to use Pippy](https://help.sugarlabs.org/pippy.html).

Autocompletion
==============

Pippy now includes code autocompletion powered by the Jedi Python library:

* Type at least 2 characters or press the dot (.) character to see suggestions
* Press Ctrl+Space to manually trigger autocompletion at any time
* Navigate the suggestion list using arrow keys
* Press Enter or double-click to insert a suggestion
* Press Escape to dismiss the autocompletion window

The autocompletion feature helps you:
* Discover available methods and attributes
* See function signatures and documentation
* Write code faster with fewer typos
* Learn the Python standard library more easily

This feature requires the `python3-jedi` package to be installed on your system.

How to upgrade?
===============

On Sugar desktop systems;
* use [My Settings](https://help.sugarlabs.org/my_settings.html), [Software Update](https://help.sugarlabs.org/my_settings.html#software-update).

How to integrate?
=================

On Debian and Ubuntu systems;

```
apt install sugar-pippy-activity
```

On Fedora systems;

```
dnf install sugar-pippy
```

Pippy depends on Python, [Sugar
Toolkit](https://github.com/sugarlabs/sugar-toolkit-gtk3), Cairo,
Telepathy, GTK+ 3,
[GtkSourceView](https://wiki.gnome.org/Projects/GtkSourceView), Pango,
Vte, Box2d and Pygame.

Pippy is started by [Sugar](https://github.com/sugarlabs/sugar).

Pippy is packaged by Linux distributions;
* [Fedora package sugar-pippy](https://src.fedoraproject.org/rpms/sugar-pippy)
* [Debian package sugar-pippy-activity](https://packages.debian.org/sugar-pippy-activity).

