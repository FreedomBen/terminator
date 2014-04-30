#!/usr/bin/python
# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""notebook.py - classes for the notebook widget"""

import gobject
import gtk

from terminator import Terminator
from config import Config
from factory import Factory
from container import Container
from editablelabel import EditableLabel
from translation import _
from util import err, dbg, enumerate_descendants

class Notebook(Container, gtk.Notebook):
    """Class implementing a gtk.Notebook container"""
    window = None

    def __init__(self, window):
        """Class initialiser"""
        if isinstance(window.get_child(), gtk.Notebook):
            err('There is already a Notebook at the top of this window')
            raise(ValueError)

        Container.__init__(self)
        gtk.Notebook.__init__(self)
        self.terminator = Terminator()
        self.window = window
        gobject.type_register(Notebook)
        self.register_signals(Notebook)
        self.configure()

        child = window.get_child()
        window.remove(child)
        window.add(self)
        self.newtab(widget=child)

        self.show_all()

    def configure(self):
        """Apply widget-wide settings"""
        # FIXME: The old reordered handler updated Terminator.terminals with
        # the new order of terminals. We probably need to preserve this for
        # navigation to next/prev terminals.
        #self.connect('page-reordered', self.on_page_reordered)
        self.set_property('homogeneous', True)
        self.set_scrollable(self.config['scroll_tabbar'])

        if self.config['tab_position'] == 'hidden' or self.config['hide_tabbar']:
            self.set_show_tabs(False)
        else:
            self.set_show_tabs(True)
            pos = getattr(gtk, 'POS_%s' % self.config['tab_position'].upper())
            self.set_tab_pos(pos)

        for tab in xrange(0, self.get_n_pages()):
            label = self.get_tab_label(self.get_nth_page(tab))
            label.update_angle()

        style = gtk.RcStyle()
        style.xthickness = 0
        style.ythickness = 0
        self.modify_style(style)

    def create_layout(self, layout):
        """Apply layout configuration"""
        def child_compare(a, b):
            order_a = children[a]['order']
            order_b = children[b]['order']

            if (order_a == order_b):
                return 0
            if (order_a < order_b):
                return -1
            if (order_a > order_b):
                return 1

        if not layout.has_key('children'):
            err('layout specifies no children: %s' % layout)
            return

        children = layout['children']
        if len(children) <= 1:
            #Notebooks should have two or more children
            err('incorrect number of children for Notebook: %s' % layout)
            return

        num = 0
        keys = children.keys()
        keys.sort(child_compare)

        for child_key in keys:
            child = children[child_key]
            dbg('Making a child of type: %s' % child['type'])
            if child['type'] == 'Terminal':
                pass
            elif child['type'] == 'VPaned':
                page = self.get_nth_page(num)
                self.split_axis(page, True)
            elif child['type'] == 'HPaned':
                page = self.get_nth_page(num)
                self.split_axis(page, False)
            num = num + 1

        num = 0
        for child_key in keys:
            page = self.get_nth_page(num)
            if not page:
                # This page does not yet exist, so make it
                self.newtab(children[child_key])
                page = self.get_nth_page(num)
            if layout.has_key('labels'):
                labeltext = layout['labels'][num]
                if labeltext and labeltext != "None":
                    label = self.get_tab_label(page)
                    label.set_custom_label(labeltext)
            page.create_layout(children[child_key])
            num = num + 1

    def split_axis(self, widget, vertical=True, cwd=None, sibling=None, widgetfirst=True):
        """Split the axis of a terminal inside us"""
        dbg('called for widget: %s' % widget)
        order = None
        page_num = self.page_num(widget)
        if page_num == -1:
            err('Notebook::split_axis: %s not found in Notebook' % widget)
            return

        label = self.get_tab_label(widget)
        self.remove(widget)

        maker = Factory()
        if vertical:
            container = maker.make('vpaned')
        else:
            container = maker.make('hpaned')

        if not sibling:
            sibling = maker.make('terminal')
            sibling.set_cwd(cwd)
            sibling.spawn_child()
            if widget.group and self.config['split_to_group']:
                sibling.set_group(None, widget.group)
        if self.config['always_split_with_profile']:
            sibling.force_set_profile(None, widget.get_profile())

        self.insert_page(container, None, page_num)
        self.set_tab_reorderable(container, True)
        self.set_tab_label(container, label)
        self.show_all()

        order = [widget, sibling]
        if widgetfirst is False:
            order.reverse()

        for terminal in order:
            container.add(terminal)
        self.set_current_page(page_num)

        self.show_all()
        terminal.grab_focus()

    def add(self, widget, metadata=None):
        """Add a widget to the container"""
        dbg('adding a new tab')
        self.newtab(widget=widget, metadata=metadata)

    def remove(self, widget):
        """Remove a widget from the container"""
        page_num = self.page_num(widget)
        if page_num == -1:
            err('%s not found in Notebook. Actual parent is: %s' % 
                    (widget, widget.get_parent()))
            return(False)
        self.remove_page(page_num)
        self.disconnect_child(widget)
        return(True)

    def replace(self, oldwidget, newwidget):
        """Replace a tab's contents with a new widget"""
        page_num = self.page_num(oldwidget)
        self.remove(oldwidget)
        self.add(newwidget)
        self.reorder_child(newwidget, page_num)

    def get_child_metadata(self, widget):
        """Fetch the relevant metadata for a widget which we'd need
        to recreate it when it's readded"""
        metadata = {}
        metadata['tabnum'] = self.page_num(widget)
        label = self.get_tab_label(widget)
        if not label:
            dbg('unable to find label for widget: %s' % widget)
        else:
            metadata['label'] = label.get_label()
        return metadata

    def get_children(self):
        """Return an ordered list of our children"""
        children = []
        for page in xrange(0,self.get_n_pages()):
            children.append(self.get_nth_page(page))
        return(children)

    def newtab(self, debugtab=False, widget=None, cwd=None, metadata=None, profile=None):
        """Add a new tab, optionally supplying a child widget"""
        dbg('making a new tab')
        maker = Factory()
        top_window = self.get_toplevel()

        if not widget:
            widget = maker.make('Terminal')
            if cwd:
                widget.set_cwd(cwd)
            widget.spawn_child(debugserver=debugtab)
        if profile and self.config['always_split_with_profile']:
            widget.force_set_profile(None, profile)

        signals = {'close-term': self.wrapcloseterm,
                   'split-horiz': self.split_horiz,
                   'split-vert': self.split_vert,
                   'title-change': self.propagate_title_change,
                   'unzoom': self.unzoom,
                   'tab-change': top_window.tab_change,
                   'group-all': top_window.group_all,
                   'ungroup-all': top_window.ungroup_all,
                   'group-tab': top_window.group_tab,
                   'ungroup-tab': top_window.ungroup_tab,
                   'move-tab': top_window.move_tab,
                   'tab-new': [top_window.tab_new, widget],
                   'navigate': top_window.navigate_terminal}

        if maker.isinstance(widget, 'Terminal'):
            for signal in signals:
                args = []
                handler = signals[signal]
                if isinstance(handler, list):
                    args = handler[1:]
                    handler = handler[0]
                self.connect_child(widget, signal, handler, *args)

        if metadata and metadata.has_key('tabnum'):
            tabpos = metadata['tabnum']
        else:
            tabpos = -1

        label = TabLabel(self.window.get_title(), self)
        if metadata and metadata.has_key('label'):
            dbg('creating TabLabel with text: %s' % metadata['label'])
            label.set_custom_label(metadata['label'])
        label.connect('close-clicked', self.closetab)

        label.show_all()
        widget.show_all()

        dbg('inserting page at position: %s' % tabpos)
        self.insert_page(widget, None, tabpos)
        self.set_tab_label(widget, label)
        self.set_tab_label_packing(widget, not self.config['scroll_tabbar'],
                                   not self.config['scroll_tabbar'],
                                   gtk.PACK_START)

        self.set_tab_reorderable(widget, True)
        self.set_current_page(tabpos)
        self.show_all()
        if maker.isinstance(widget, 'Terminal'):
            widget.grab_focus()

    def wrapcloseterm(self, widget):
        """A child terminal has closed"""
        dbg('Notebook::wrapcloseterm: called on %s' % widget)
        if self.closeterm(widget):
            dbg('Notebook::wrapcloseterm: closeterm succeeded')
            self.hoover()
        else:
            dbg('Notebook::wrapcloseterm: closeterm failed')

    def closetab(self, widget, label):
        """Close a tab"""
        tabnum = None
        try:
            nb = widget.notebook
        except AttributeError:
            err('TabLabel::closetab: called on non-Notebook: %s' % widget)
            return

        for i in xrange(0, nb.get_n_pages() + 1):
            if label == nb.get_tab_label(nb.get_nth_page(i)):
                tabnum = i
                break

        if tabnum is None:
            err('TabLabel::closetab: %s not in %s. Bailing.' % (label, nb))
            return

        maker = Factory()
        child = nb.get_nth_page(tabnum)

        if maker.isinstance(child, 'Terminal'):
            dbg('Notebook::closetab: child is a single Terminal')
            child.close()
            # FIXME: We only do this del and return here to avoid removing the
            # page below, which child.close() implicitly does
            del(label)
            return
        elif maker.isinstance(child, 'Container'):
            dbg('Notebook::closetab: child is a Container')
            dialog = self.construct_confirm_close(self.window, _('tab'))
            result = dialog.run()
            dialog.destroy()

            if result == gtk.RESPONSE_ACCEPT:
                containers = None
                objects = None
                containers, objects = enumerate_descendants(child)

                while len(objects) > 0:
                    descendant = objects.pop()
                    descendant.close()
                    while gtk.events_pending():
                        gtk.main_iteration()
                return
            else:
                dbg('Notebook::closetab: user cancelled request')
                return
        else:
            err('Notebook::closetab: child is unknown type %s' % child)
            return

        nb.remove_page(tabnum)
        del(label)

    def resizeterm(self, widget, keyname):
        """Handle a keyboard event requesting a terminal resize"""
        raise NotImplementedError('resizeterm')

    def zoom(self, widget, fontscale = False):
        """Zoom a terminal"""
        raise NotImplementedError('zoom')

    def unzoom(self, widget):
        """Unzoom a terminal"""
        raise NotImplementedError('unzoom')

    def find_tab_root(self, widget):
        """Look for the tab child which is or ultimately contains the supplied
        widget"""
        parent = widget.get_parent()
        previous = parent

        while parent is not None and parent is not self:
            previous = parent
            parent = parent.get_parent()

        if previous == self:
            return(widget)
        else:
            return(previous)

    def update_tab_label_text(self, widget, text):
        """Update the text of a tab label"""
        notebook = self.find_tab_root(widget)
        label = self.get_tab_label(notebook)
        if not label:
            err('Notebook::update_tab_label_text: %s not found' % widget)
            return
        
        label.set_label(text)

    def hoover(self):
        """Clean up any empty tabs and if we only have one tab left, die"""
        numpages = self.get_n_pages()
        while numpages > 0:
            numpages = numpages - 1
            page = self.get_nth_page(numpages)
            if not page:
                dbg('Removing empty page: %d' % numpages)
                self.remove_page(numpages)

        if self.get_n_pages() == 1:
            dbg('Last page, removing self')
            child = self.get_nth_page(0)
            self.remove_page(0)
            parent = self.get_parent()
            parent.remove(self)
            self.cnxids.remove_all()
            parent.add(child)
            del(self)
            # Find the last terminal in the new parent and give it focus
            terms = parent.get_visible_terminals()
            terms.keys()[-1].grab_focus()

class TabLabel(gtk.HBox):
    """Class implementing a label widget for Notebook tabs"""
    notebook = None
    terminator = None
    config = None
    label = None
    icon = None
    button = None

    __gsignals__ = {
            'close-clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_OBJECT,)),
    }

    def __init__(self, title, notebook):
        """Class initialiser"""
        gtk.HBox.__init__(self)
        self.__gobject_init__()

        self.notebook = notebook
        self.terminator = Terminator()
        self.config = Config()

        self.label = EditableLabel(title)
        self.update_angle()

        self.pack_start(self.label, True, True)

        self.update_button()
        self.show_all()

    def set_label(self, text):
        """Update the text of our label"""
        self.label.set_text(text)

    def get_label(self):
        return self.label.get_text()

    def set_custom_label(self, text):
        """Set a permanent label as if the user had edited it"""
        self.label.set_text(text)
        self.label.set_custom()

    def get_custom_label(self):
        """Return a custom label if we have one, otherwise None"""
        if self.label.is_custom():
            return(self.label.get_text())
        else:
            return(None)

    def update_button(self):
        """Update the state of our close button"""
        if not self.config['close_button_on_tab']:
            if self.button:
                self.button.remove(self.icon)
                self.remove(self.button)
                del(self.button)
                del(self.icon)
                self.button = None
                self.icon = None
            return

        if not self.button:
            self.button = gtk.Button()
        if not self.icon:
            self.icon = gtk.Image()
            self.icon.set_from_stock(gtk.STOCK_CLOSE,
                                     gtk.ICON_SIZE_MENU)

        self.button.set_focus_on_click(False)
        self.button.set_relief(gtk.RELIEF_NONE)
        style = gtk.RcStyle()
        style.xthickness = 0
        style.ythickness = 0
        self.button.modify_style(style)
        self.button.add(self.icon)
        self.button.connect('clicked', self.on_close)
        self.button.set_name('terminator-tab-close-button')
        if hasattr(self.button, 'set_tooltip_text'):
            self.button.set_tooltip_text(_('Close Tab'))
        self.pack_start(self.button, False, False)
        self.show_all()

    def update_angle(self):
        """Update the angle of a label"""
        position = self.notebook.get_tab_pos()
        if position == gtk.POS_LEFT:
            if hasattr(self, 'set_orientation'):
                self.set_orientation(gtk.ORIENTATION_VERTICAL)
            self.label.set_angle(90)
        elif position == gtk.POS_RIGHT:
            if hasattr(self, 'set_orientation'):
                self.set_orientation(gtk.ORIENTATION_VERTICAL)
            self.label.set_angle(270)
        else:
            if hasattr(self, 'set_orientation'):
                self.set_orientation(gtk.ORIENTATION_HORIZONTAL)
            self.label.set_angle(0)

    def on_close(self, _widget):
        """The close button has been clicked. Destroy the tab"""
        self.emit('close-clicked', self)

# vim: set expandtab ts=4 sw=4:
