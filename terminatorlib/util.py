#!/usr/bin/python
#    Terminator.util - misc utility functions
#    Copyright (C) 2006-2010  cmsj@tenshu.net
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, version 2 only.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""Terminator.util - misc utility functions

>>> a = {'foo': 'bar', 'baz': 'bjonk'}
>>> b = {'foo': 'far', 'baz': 'bjonk'}
>>> dict_diff(a, b)
{'foo': 'far'}

"""

import sys
import gtk
import os
import pwd
import inspect
import uuid

# set this to true to enable debugging output
DEBUG = False
# set this to true to additionally list filenames in debugging
DEBUGFILES = False
# list of classes to show debugging for. empty list means show all classes
DEBUGCLASSES = []
# list of methods to show debugging for. empty list means show all methods
DEBUGMETHODS = []

def dbg(log = ""):
    """Print a message if debugging is enabled"""
    if DEBUG:
        stackitem = inspect.stack()[1]
        parent_frame = stackitem[0]
        method = parent_frame.f_code.co_name
        names, varargs, keywords, local_vars = inspect.getargvalues(parent_frame)
        try:
            self_name = names[0]
            classname = local_vars[self_name].__class__.__name__
        except IndexError:
            classname = "noclass"
        if DEBUGFILES:
            line = stackitem[2]
            filename = parent_frame.f_code.co_filename
            extra = " (%s:%s)" % (filename, line)
        else:
            extra = ""
        if DEBUGCLASSES != [] and classname not in DEBUGCLASSES:
            return
        if DEBUGMETHODS != [] and method not in DEBUGMETHODS:
            return
        try:
            print >> sys.stderr, "%s::%s: %s%s" % (classname, method, log, extra)
        except IOError:
            pass

def err(log = ""):
    """Print an error message"""
    try:
        print >> sys.stderr, log
    except IOError:
        pass

def gerr(message = None):
    """Display a graphical error. This should only be used for serious
    errors as it will halt execution"""

    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, message)
    dialog.run()
    dialog.destroy()

def has_ancestor(widget, wtype):
    """Walk up the family tree of widget to see if any ancestors are of type"""
    while widget:
        widget = widget.get_parent()
        if isinstance(widget, wtype):
            return(True)
    return(False)

def path_lookup(command):
    '''Find a command in our path'''
    if os.path.isabs(command):
        if os.path.isfile(command):
            return(command)
        else:
            return(None)
    elif command[:2] == './' and os.path.isfile(command):
        dbg('path_lookup: Relative filename %s found in cwd' % command)
        return(command)

    try:
        paths = os.environ['PATH'].split(':')
        if len(paths[0]) == 0: 
            raise(ValueError)
    except (ValueError, NameError):
        dbg('path_lookup: PATH not set in environment, using fallbacks')
        paths = ['/usr/local/bin', '/usr/bin', '/bin']

    dbg('path_lookup: Using %d paths: %s' % (len(paths), paths))

    for path in paths:
        target = os.path.join(path, command)
        if os.path.isfile(target):
            dbg('path_lookup: found %s' % target)
            return(target)

    dbg('path_lookup: Unable to locate %s' % command)

def shell_lookup():
    """Find an appropriate shell for the user"""
    try:
        usershell = pwd.getpwuid(os.getuid())[6]
    except KeyError:
        usershell = None
    shells = [usershell, 'bash', 'zsh', 'tcsh', 'ksh', 'csh', 'sh']

    for shell in shells:
        if shell is None:
            continue
        elif os.path.isfile(shell):
            return(shell)
        else:
            rshell = path_lookup(shell)
            if rshell is not None:
                dbg('shell_lookup: Found %s at %s' % (shell, rshell))
                return(rshell)
    dbg('shell_lookup: Unable to locate a shell')

def widget_pixbuf(widget, maxsize=None):
    """Generate a pixbuf of a widget"""
    if gtk.gtk_version < (2, 14):
        return(None)

    pixmap = widget.get_snapshot()
    (width, height) = pixmap.get_size()
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, width, height)
    pixbuf.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, width,
            height)

    longest = max(width, height)

    if maxsize is not None:
        factor = float(maxsize) / float(longest)

    if not maxsize or (width * factor) > width or (height * factor) > height:
        factor = 1

    scaledpixbuf = pixbuf.scale_simple(int(width * factor), int(height * factor), gtk.gdk.INTERP_BILINEAR)

    return(scaledpixbuf)

def get_config_dir():
    """Expand all the messy nonsense for finding where ~/.config/terminator
    really is"""
    try:
        configdir = os.environ['XDG_CONFIG_HOME']
    except KeyError:
        configdir = os.path.join(os.path.expanduser('~'), '.config')

    dbg('Found config dir: %s' % configdir)
    return(os.path.join(configdir, 'terminator'))

def dict_diff(reference, working):
    """Examine the values in the supplied working set and return a new dict
    that only contains those values which are different from those in the
    reference dictionary"""

    result = {}

    for key in reference:
        if reference[key] != working[key]:
            result[key] = working[key]

    return(result)

# Helper functions for directional navigation
def get_edge(allocation, direction):
    """Return the edge of the supplied allocation that we will care about for
    directional navigation"""
    if direction == 'left':
        edge = allocation.x
    elif direction == 'up':
        edge = allocation.y
    elif direction == 'right':
        edge = allocation.x + allocation.width
    elif direction == 'down':
        edge = allocation.y + allocation.height
    else:
        raise ValueError('unknown direction %s' % direction)
    
    return(edge)

def get_nav_possible(edge, allocation, direction):
    """Check if the supplied allocation is in the right direction of the
    supplied edge"""
    if direction == 'left':
        return((allocation.x + allocation.width) <= edge)
    elif direction == 'right':
        return(allocation.x >= edge)
    elif direction == 'up':
        return((allocation.y + allocation.height) <= edge)
    elif direction == 'down':
        return(allocation.y >= edge)
    else:
        raise ValueError('Unknown direction: %s' % direction)

def get_nav_offset(edge, allocation, direction):
    """Work out how far edge is from a particular point on the allocation
    rectangle, in the given direction"""
    if direction == 'left':
        return(edge - (allocation.x + allocation.width))
    elif direction == 'right':
        return(edge + allocation.x)
    elif direction == 'up':
        return(edge - (allocation.y - allocation.height))
    elif direction == 'down':
        return(edge + allocation.y)
    else:
        raise ValueError('Unknown direction: %s' % direction)

def get_nav_tiebreak(direction, cursor_x, cursor_y, rect):
    """We have multiple candidate terminals. Pick the closest by cursor
    position"""
    if direction in ['left', 'right']:
        return(cursor_y >= rect.y and cursor_y <= (rect.y + rect.height))
    elif direction in ['up', 'down']:
        return(cursor_x >= rect.x and cursor_x <= (rect.x + rect.width))
    else:
        raise ValueError('Unknown direction: %s' % direction)

def enumerate_descendants(parent):
    """Walk all our children and build up a list of containers and
    terminals"""
    # FIXME: Does having to import this here mean we should move this function
    # back to Container?
    from factory import Factory

    containerstmp = []
    containers = []
    terminals = []
    maker = Factory()

    if parent is None:
        err('no parent widget specified')
        return

    for descendant in parent.get_children():
        if maker.isinstance(descendant, 'Container'):
            containerstmp.append(descendant)
        elif maker.isinstance(descendant, 'Terminal'):
            terminals.append(descendant)

        while len(containerstmp) > 0:
            child = containerstmp.pop(0)
            for descendant in child.get_children():
                if maker.isinstance(descendant, 'Container'):
                    containerstmp.append(descendant)
                elif maker.isinstance(descendant, 'Terminal'):
                    terminals.append(descendant)
            containers.append(child)

    dbg('%d containers and %d terminals fall beneath %s' % (len(containers), 
        len(terminals), parent))
    return(containers, terminals)

def make_uuid():
    """Generate a UUID for an object"""
    return uuid.uuid4()

def inject_uuid(target):
    """Inject a UUID into an existing object"""
    uuid = make_uuid()
    if not hasattr(target, "uuid") or target.uuid == None:
        dbg("Injecting UUID %s into: %s" % (uuid, target))
        target.uuid = uuid
    else:
        dbg("Object already has a UUID: %s" % target)

