# NordVPN interface class
# Provides an interface with the NordVPN Linux client application

import re
import subprocess
from enum import Enum, unique


@unique
class ConnectionStatus(Enum):
    """
    Connection status to the VPN
    """
    CONNECTED = 'Connected'
    DISCONNECTED = 'Disconnected'
    WAITING = 'Connecting'


@unique
class Settings(Enum):
    """
    Represents the settings available for the NordVPN client application.
    Each value is the exact match of the setting name
    """
    PROTOCOL = "Protocol"
    KILL_SWITCH = "Kill Switch"
    CYBER_SEC = "CyberSec"
    OBFUSCATE = "Obfuscate"
    AUTO_CONNECT = "Auto-connect"
    DNS = "DNS"
    NOTIFY = "Notify"
    TECHNOLOGY = "Technology"


class NordVPNStatus():
    """
    Status of the NordVPN client app
    """
    @unique
    class Param(Enum):
        """
        Parameters that compose the client app status
        """
        STATUS = 'Status'
        CURRENT_SERVER = 'Current server'
        COUNTRY = 'Country'
        CITY = 'City'
        IP = 'Your new IP'
        PROTOCOL = 'Current protocol'
        TRANSFER = 'Transfer'
        UPTIME = 'Uptime'

    def __init__(self):
        self.raw_status = 'Unknown'
        self.data = {
            NordVPNStatus.Param.STATUS: ConnectionStatus.WAITING,
            NordVPNStatus.Param.CURRENT_SERVER: 'Unknown',
            NordVPNStatus.Param.COUNTRY: 'Unknown',
            NordVPNStatus.Param.CITY: 'Unknown',
            NordVPNStatus.Param.IP: 'Unknown',
            NordVPNStatus.Param.PROTOCOL: 'Unknown',
            NordVPNStatus.Param.TRANSFER: 'Unknown',
            NordVPNStatus.Param.UPTIME: 'Unknown'
        }
        self.warnings = set()

    def update(self, raw_status):
        # Save the raw status string
        self.raw_status = raw_status

        # If there are warnings, show them in the raw_status
        if len(self.warnings) > 0:
            self.raw_status = '\n\r'.join([self.raw_status] + sorted(self.warnings))
            self.data[NordVPNStatus.Param.STATUS] = ConnectionStatus.WAITING
            return

        # Try to parse each parameter
        try:
            for param in NordVPNStatus.Param:
                # Status needs to be converted and must always be present
                if param == NordVPNStatus.Param.STATUS:
                    status = self._parse_param(
                        NordVPNStatus.Param.STATUS.value, raw_status, True)
                    self.data[NordVPNStatus.Param.STATUS] = ConnectionStatus(
                        status)
                else:
                    # Parse parameter and store its value
                    value = self._parse_param(param.value, raw_status)
                    self.data[param] = value
        except Exception as e:
            self.data[NordVPNStatus.Param.STATUS] = ConnectionStatus.WAITING

    def add_warning(self, message):
        """
        Add a warning message to the raw_status
        """
        self.warnings.add(message)

    def clear_warnings(self):
        """
        Clear all the warning messages
        """
        self.warnings.clear()

    def _parse_param(self, param, source, throw=False):
        """
        Parse the parameter from the source string. If throw is True, an exception
        is thrown when the parameter is not found.
        Return the value string of the parsed parameter key
        """
        match = re.search(r"{}:\s(.*)".format(param), source)
        if match is None and throw:
            raise Exception("Unable to parse {} from {}".format(param, source))
        elif match is None:
            return "Unknown"
        return match.group(1).strip()


class NordVPN(object):
    """
    NordVPN

    Args:
        nordvpn: Nordvpn instance for connecting/disconnecting and
        checking the status of the connection

    Returns:
        Instance of Indicator class
    """

    def __init__(self):
        self.status = NordVPNStatus()
        self.UPDATE_WARNING = 'A new version of NordVPN is available! Please update the application.'
        self.LOGIN_WARNING = 'Please enter your login details.'

# Connection interfaces

    def connect(self, _):
        """
        Runs command to connect with a NordVPN server

        Args:
            _: As required by AppIndicator
        """
        output = self._run_command("nordvpn connect")
        if not self._output_has_warnings(output):
            self.status.clear_warnings()

    def connect_to_country(self, country):
        """
        Runs command to connect to a NordVPN server in the specified country

        Args:
            country: Country name as string
        """
        output = self._run_command(
            "nordvpn connect {}".format(country.replace(' ', '_')))
        if not self._output_has_warnings(output):
            self.status.clear_warnings()

    def connect_to_group(self, group):
        """
        Connect to a server group
        """
        output = self._run_command(
            "nordvpn connect {}".format(group.replace(' ', '_')))
        if not self._output_has_warnings(output):
            self.status.clear_warnings()

    def connect_to_city(self, city):
        """
        Connect to a specific city server
        """
        output = self._run_command(
            "nordvpn connect {}".format(city.replace(' ', '_')))
        if not self._output_has_warnings(output):
            self.status.clear_warnings()

    def disconnect(self, _):
        """
        Runs command to disconnect with the currently connected NordVPN server

        Args:
            _: As required by AppIndicator
        """
        output = self._run_command("nordvpn disconnect")
        if not self._output_has_warnings(output):
            self.status.clear_warnings()

# Getters and Setters interfaces

    def get_status(self):
        """
        Returns the current status of the VPN connection as a string
        """
        self._status_check()
        return self.status

    def get_countries(self):
        """
        Returns a list of string representing the available countries
        """
        raw_countries = self._run_command('nordvpn countries')
        if raw_countries is None:
            return []
        return self._parse_words(raw_countries)

    def get_settings(self):
        """
        Read the current settings from the client app and return them as dictionary

        Returns:
            - A dictionary {Setting:Value} where Setting is a instance of Settings Enum
        """
        output = self._run_command('nordvpn settings')
        if output is None:
            return {}
        return self._parse_settings(output)

    def set_settings(self, settings):
        """
        Handle the update of nord vpn settings from the indicator app

        Args:
            - settings: a dict {Settings : value} representing settings to set.
                        Settings will be updated only if their related key is in the dict
        """
        for key, value in settings.items():
            setting = value
            if key == Settings.AUTO_CONNECT:
                if value == 'Off':
                    setting = False
                elif value == 'Automatic':
                    setting = True
                else:
                    setting = 'on {}'.format(value.lower())
            self._run_command('nordvpn set {} {}'.format(
                key.value.replace(' ', '').replace('-', '').lower(), str(setting).lower()))

    def get_groups(self):
        """
        Returns a list of string representing the available groups
        """
        groups = self._run_command('nordvpn groups')
        if groups is None:
            return []
        return self._parse_words(groups)

    def get_cities(self, country):
        """
        Return the list of cities available for the given country
        """
        cities = self._run_command(
            'nordvpn cities {}'.format(country.replace(' ', '_')))
        if cities is None:
            return []
        return self._parse_words(cities)

# Private functions

    def _run_command(self, command):
        """
        Runs bash commands and notifies on errors

        Args:
            command: Bash command to run

        Returns:
            Output of the bash command
        """
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        # Decode from bytes to string
        output = output.decode()
        return output

    def _output_has_warnings(self, output):
        """
        Check if a command ouput stream contains warning strings
        """
        message = "Unknown error"
        # Check warnings in output stream
        if self.UPDATE_WARNING in output:
            message = 'Warning: new version of the nordvpn client available'
        elif self.LOGIN_WARNING in output:
            message = 'Warning: Please login to NordVPN'
        else:
            return False
        self.status.add_warning(message)
        return True

    def _status_check(self):
        """
        Checks if an IP is outputted by the NordVPN status command

        Args:
            _: As required by AppIndicator
        """
        output = self._run_command("nordvpn status")
        if output is not None:
            raw = output.strip()
            self.status.update(raw)

    def _parse_words(self, raw):
        """
        Search for any separated words from the raw input string.
        Returns a list of the extracted words sorted alphabetically.
        """
        if raw is None:
            return []
        parsed_list = re.findall(r'(\w{2,})+', raw)
        if parsed_list is None:
            return []
        # Sort the list and replace nasty characters
        parsed_list.sort()
        parsed_list = list(map(lambda r: r.replace('_', ' '), parsed_list))
        return parsed_list

    def _parse_settings(self, raw):
        """
        Parse the raw output of "nordvpn settings" command.
        Returns a dictionary {Setting:Value} where Setting is a instance of Settings Enum
        """
        settings = {}
        if raw is None:
            return []
        # Parse parameters with len > 2 to discard - characters at the beginning
        match = re.findall(r"(\S{2,}\s*\S*):\s*(\S+)", raw)
        if match is None:
            return []
        for key, value in match:
            # PROTOCOL has special values
            if key == Settings.PROTOCOL.value:
                value = 'enabled' if value == 'TCP' else 'disabled'
            # TECHNOLOGY has special values
            if key == Settings.TECHNOLOGY.value:
                value = 'enabled' if value == 'NordLynx' else 'disabled'
            # Create Settings instance
            settings[Settings(
                key)] = True if value == 'enabled' else False
        return settings
