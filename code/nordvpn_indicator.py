#!/usr/bin/python
"""
Adds icon to notification tray that allows for connecting
and disconnecting to NordVPN
"""

import os
import signal
import threading
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator

from nordvpn import NordVPN, ConnectionStatus, Settings, NordVPNStatus


APPINDICATOR_ID = 'nordvpn_tray_icon'
TIMER_SECONDS = 5.0

class Indicator(object):
    """
    Indicator provides tray icon with menu, handles user interaction
    and sets a timer for checking the VPN status

    Args:
        nordvpn: Nordvpn instance for connecting/disconnecting and
        checking the status of the connection

    Returns:
        Instance of Indicator class
    """
    def __init__(self, nordvpn):
        self.nordvpn = nordvpn

        # Add indicator
        self.indicator = appindicator.Indicator.new(
            APPINDICATOR_ID,
            self.get_icon_path(ConnectionStatus.WAITING),
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # Set recurrent timer for checking VPN status
        self.status_check_loop()
        gtk.main()

    def status_check_loop(self):
        """
        Sets timer in recurrent loop that executes a VPN status check
        """
        self.update()
        self.timer = threading.Timer(TIMER_SECONDS, self.status_check_loop)
        self.timer.start()

    def update(self):
        """
        Updates the icon and the menu status item
        """
        status = self.nordvpn.get_status()
        self.status_label.set_label(status.raw_status)
        self.indicator.set_icon_full(self.get_icon_path(status.data[NordVPNStatus.Param.STATUS]),'')

    @staticmethod
    def get_icon_path(connected):
        """
        Returns the correct icon in response to the connection status

        Args:
            connected: Connected status ConnectionStatus object
        """
        if connected == ConnectionStatus.CONNECTED:
            filename = 'nordvpn_connected.png'
        elif connected == ConnectionStatus.DISCONNECTED:
            filename = 'nordvpn_disconnected.png'
        else:
            filename = 'nordvpn_waiting.png'
        return os.path.dirname(os.path.realpath(__file__)) + '/' + filename

    def build_menu(self):
        """
        Builds menu for the tray icon
        """
        main_menu = gtk.Menu()

        # Create a Connect submenu
        menu_connect = gtk.Menu()
        item_connect = gtk.MenuItem(label='Connect')
        item_connect.set_submenu(menu_connect)
        main_menu.append(item_connect)

        # First item is to connect automatically
        item_connect_auto = gtk.MenuItem(label='Auto')
        item_connect_auto.connect('activate', self.auto_connect_cb)
        menu_connect.append(item_connect_auto)

        # Second item is submenu to select the country
        countries = self.nordvpn.get_countries()
        countries_menu = gtk.Menu()
        item_connect_country = gtk.MenuItem(label='Countries')
        item_connect_country.set_submenu(countries_menu)
        for country in countries:
            item = gtk.MenuItem(label=country)
            item.connect('activate', self.country_connect_cb)
            countries_menu.append(item)
        menu_connect.append(item_connect_country)

        # Next item is submenu to select a specific city
        cities_menu = gtk.Menu()
        item_connect_city = gtk.MenuItem(label='Cities')
        item_connect_city.set_submenu(cities_menu)
        for country in countries:
            # Draw the country as disabled
            item_country = gtk.MenuItem(label=country)
            item_country.set_sensitive(False)
            cities_menu.append(item_country)
            # List the cities below
            cities = self.nordvpn.get_cities(country)
            for city in cities:
                item_city = gtk.MenuItem(label=city)
                item_city.connect('activate', self.city_connect_cb)
                cities_menu.append(item_city)
        menu_connect.append(item_connect_city)

        # Next item is submenu to select a server group
        groups = self.nordvpn.get_groups()
        groups_menu = gtk.Menu()
        item_connect_group = gtk.MenuItem(label='Groups')
        item_connect_group.set_submenu(groups_menu)
        for g in groups:
            item = gtk.MenuItem(label=g)
            item.connect('activate', self.group_connect_cb)
            groups_menu.append(item)
        menu_connect.append(item_connect_group)

        # Disconnect item
        item_disconnect = gtk.MenuItem(label='Disconnect')
        item_disconnect.connect('activate', self.nordvpn.disconnect)
        main_menu.append(item_disconnect)

        # Create a submenu for the connection status
        menu_status = gtk.Menu()
        item_status = gtk.MenuItem(label='Status')
        item_status.set_submenu(menu_status)
        main_menu.append(item_status)

        # Add a label to show the current status details
        self.status_label = gtk.MenuItem(label='')
        menu_status.append(self.status_label)
        self.status_label.set_sensitive(False)

        # Define the Settings menu entry
        item_settings = gtk.MenuItem(label='Settings...')
        item_settings.connect('activate', self.display_settings_window)
        main_menu.append(item_settings)

        item_quit = gtk.MenuItem(label='Quit')
        item_quit.connect('activate', self.quit)
        main_menu.append(item_quit)

        main_menu.show_all()
        return main_menu

    def quit(self, _):
        """
        Cancels the timer, removes notifications, removes tray icon resulting
        in quitting the application
        """
        self.timer.cancel()
        gtk.main_quit()

    def country_connect_cb(self, btn_toggled):
        """
        Callback function to handle the connection of a selected country
        """
        self.nordvpn.disconnect(None)
        self.nordvpn.connect_to_country(btn_toggled.get_label())

    def auto_connect_cb(self, _):
        """
        Callback to handle connection to auto server
        """
        self.nordvpn.disconnect(None)
        self.nordvpn.connect(None)

    def display_settings_window(self, widget):
        """
        Display a new window showing the settings of the NordVPN client app
        """
        window = SettingsWindow(self.nordvpn)
        window.show_all()

    def group_connect_cb(self, menu_item):
        """
        Callback to connect to a server group
        """
        self.nordvpn.disconnect(None)
        self.nordvpn.connect_to_group(menu_item.get_label())

    def city_connect_cb(self, menu_item):
        """
        Callback to connet to a city server
        """
        self.nordvpn.disconnect(None)
        self.nordvpn.connect_to_city(menu_item.get_label())

class SettingsWindow(gtk.Window):
    """
    GTK window widget to display NordVPN settings

    Args:
        - settings: dict {Settings:value} representing the configuration to display
        - callback: function accepting 1 argument as the "settings" dict above. Callback
                    is called to save the settings
    """
    def __init__(self, nordvpn):
        super(SettingsWindow, self).__init__()
        self.nordvpn = nordvpn
        self.set_default_size(200,200)
        self.set_title('NordVPN settings')
        self.set_border_width(8)
        #self.set_position(WIN_POS_CENTER)
        self.set_default_icon_from_file(os.path.dirname(os.path.realpath(__file__)) + '/nordvpn_disconnected.png')
        self.set_focus()
        # Build window layout
        self.add(self.create_widgets())
        # Create empty settings dict to update only settings
        # that change, and only if they change
        self.settings = {}

    def create_widgets(self):
        settings = self.nordvpn.get_settings()

        m_vbox = gtk.VBox()

        row_technology = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_technology.add(gtk.Label(Settings.TECHNOLOGY.value))
        combo_technology = gtk.ComboBoxText()
        combo_technology.set_property('name', Settings.TECHNOLOGY.value)
        combo_technology.append('openvpn', 'OpenVPN') # id and string
        combo_technology.append('nordlynx', 'NordLynx')
        combo_technology.set_active_id('nordlynx' if settings[Settings.TECHNOLOGY] else 'openvpn')
        combo_technology.connect('changed', self.on_setting_update)
        row_technology.add(combo_technology)

        row_protocol = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_protocol.add(gtk.Label(Settings.PROTOCOL.value))
        combo_protocol = gtk.ComboBoxText()
        combo_protocol.set_property('name', Settings.PROTOCOL.value)
        combo_protocol.append('udp', 'UDP') # id and string
        combo_protocol.append('tcp', 'TCP')
        combo_protocol.set_active_id('tcp' if settings[Settings.PROTOCOL] else 'udp')
        combo_protocol.connect('changed', self.on_setting_update)
        row_protocol.add(combo_protocol)

        row_kill_switch = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_kill_switch.add(gtk.Label(Settings.KILL_SWITCH.value))
        combo_kill = gtk.ComboBoxText()
        combo_kill.set_property('name', Settings.KILL_SWITCH.value)
        combo_kill.append('on', 'On')
        combo_kill.append('off', 'Off')
        combo_kill.set_active_id('on' if settings[Settings.KILL_SWITCH] else 'off')
        combo_kill.connect('changed', self.on_setting_update)
        row_kill_switch.add(combo_kill)

        row_cybersec = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_cybersec.add(gtk.Label(Settings.CYBER_SEC.value))
        combo_cybersec = gtk.ComboBoxText()
        combo_cybersec.set_property('name', Settings.CYBER_SEC.value)
        combo_cybersec.append('on', 'On')
        combo_cybersec.append('off', 'Off')
        combo_cybersec.set_active_id('on' if settings[Settings.CYBER_SEC] else 'off')
        combo_cybersec.connect('changed', self.on_setting_update)
        row_cybersec.add(combo_cybersec)

        row_obfuscate = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_obfuscate.add(gtk.Label(Settings.OBFUSCATE.value))
        combo_obfuscate = gtk.ComboBoxText()
        combo_obfuscate.set_property('name', Settings.OBFUSCATE.value)
        combo_obfuscate.append('on', 'On')
        combo_obfuscate.append('off', 'Off')
        combo_obfuscate.set_active_id('on' if settings[Settings.OBFUSCATE] else 'off')
        combo_obfuscate.connect('changed', self.on_setting_update)
        row_obfuscate.add(combo_obfuscate)

        row_notify = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_notify.add(gtk.Label(Settings.NOTIFY.value))
        combo_notify = gtk.ComboBoxText()
        combo_notify.set_property('name', Settings.NOTIFY.value)
        combo_notify.append('on', 'On')
        combo_notify.append('off', 'Off')
        combo_notify.set_active_id('on' if settings[Settings.NOTIFY] else 'off')
        combo_notify.connect('changed', self.on_setting_update)
        row_notify.add(combo_notify)

        row_autoconnect = gtk.Box(gtk.Orientation.HORIZONTAL, 4)
        row_autoconnect.add(gtk.Label(Settings.AUTO_CONNECT.value))
        combo_autoconnect = gtk.ComboBoxText()
        combo_autoconnect.set_property('name', Settings.AUTO_CONNECT.value)
        combo_autoconnect.append('off', 'Off')
        combo_autoconnect.append('auto', 'Automatic')
        for country in self.nordvpn.get_countries():
            combo_autoconnect.append(country.lower(), country)
        combo_autoconnect.set_active_id('auto' if settings[Settings.AUTO_CONNECT] else 'off')
        combo_autoconnect.connect('changed', self.on_setting_update)
        row_autoconnect.add(combo_autoconnect)

        # FIXME The DNS setting widget is not used at the moment
        row_dns = gtk.Box(gtk.Orientation.HORIZONTAL, 4, halign=gtk.Align.FILL)
        check_dns = gtk.CheckButton(Settings.DNS.value)
        row_dns.add(check_dns)
        dns_vbox = gtk.VBox(valign=gtk.Align.END)
        entry_dns_one = gtk.Entry()
        entry_dns_one.set_placeholder_text('IP address...')
        dns_vbox.add(entry_dns_one)
        entry_dns_two = gtk.Entry()
        entry_dns_two.set_placeholder_text('IP address...')
        dns_vbox.add(entry_dns_two)
        entry_dns_three = gtk.Entry()
        entry_dns_three.set_placeholder_text('IP address...')
        dns_vbox.add(entry_dns_three)
        dns_vbox.set_sensitive(False)
        row_dns.add(dns_vbox)

        row_blank = gtk.Box(gtk.Orientation.HORIZONTAL, 4, halign=gtk.Align.END)
        row_blank.add(gtk.Label())

        row_buttons = gtk.Box(gtk.Orientation.HORIZONTAL, 4, halign=gtk.Align.END)
        button_apply = gtk.Button('Apply')
        button_apply.connect('clicked', self.on_apply)
        button_close = gtk.Button('Close')
        button_close.connect('clicked', self.on_close)
        row_buttons.add(button_close)
        row_buttons.add(button_apply)

        m_vbox.pack_start(row_technology, True, False, 0)
        m_vbox.pack_start(row_protocol, True, False, 0)
        m_vbox.pack_start(row_kill_switch, True, False, 0)
        m_vbox.pack_start(row_cybersec, True, False, 0)
        m_vbox.pack_start(row_obfuscate, True, False, 0)
        m_vbox.pack_start(row_notify, True, False, 0)
        m_vbox.pack_start(row_autoconnect, True, False, 0)
        m_vbox.pack_start(row_dns, True, False, 0)
        m_vbox.pack_start(row_blank, True, False, 0)
        m_vbox.pack_start(row_buttons, True, False, 0)
        return m_vbox

    def on_close(self, widget):
        """
        Close the settings window
        """
        self.destroy()

    def on_apply(self, widget):
        """
        Save the selected settings and pass them through the result callback
        """
        # Call the function to actually set the settings
        self.nordvpn.set_settings(self.settings)
        # Reset internal member to avoid set again the same settings
        self.settings = {}

    def on_setting_update(self, widget):
        """
        Callback to handle a selection from the settings widgets
        """
        if widget.get_name() == Settings.PROTOCOL.value:
            self.settings[Settings.PROTOCOL] = widget.get_active_text()
        elif widget.get_name() == Settings.KILL_SWITCH.value:
            self.settings[Settings.KILL_SWITCH] = (widget.get_active_text().lower() == 'on')
        elif widget.get_name() == Settings.CYBER_SEC.value:
            self.settings[Settings.CYBER_SEC] = (widget.get_active_text().lower() == 'on')
        elif widget.get_name() == Settings.OBFUSCATE.value:
            self.settings[Settings.OBFUSCATE] = (widget.get_active_text().lower() == 'on')
        elif widget.get_name() == Settings.AUTO_CONNECT.value:
            self.settings[Settings.AUTO_CONNECT] = widget.get_active_text().replace(' ','_')
        elif widget.get_name() == Settings.NOTIFY.value:
            self.settings[Settings.NOTIFY] = (widget.get_active_text().lower() == 'on')
        elif widget.get_name() == Settings.TECHNOLOGY.value:
            self.settings[Settings.TECHNOLOGY] = widget.get_active_text()

def main():
    """
    Entry of the program

    Signal for allowing Ctrl+C interrupts
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Indicator(NordVPN())

if __name__ == '__main__':
    main()
