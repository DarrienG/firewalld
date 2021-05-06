# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2016 Red Hat, Inc.
#
# Authors:
# Thomas Woerner <twoerner@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This module contains decorators for use with and without D-Bus"""

__all__ = ["handle_exceptions", "dbus_handle_exceptions", "dbus_service_method"]

import dbus
import dbus.service
import traceback
import functools
import inspect
from dbus.exceptions import DBusException

from firewall.errors import FirewallError
from firewall import errors
from firewall.core.logger import log
from firewall.server.dbus import FirewallDBusException

############################################################################
#
# Exception handler decorators
#
############################################################################

def handle_exceptions(func):
    """Decorator to handle exceptions and log them. Used if not conneced
    to D-Bus.
    """
    @functools.wraps(func)
    def _impl(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FirewallError as error:
            log.debug1(traceback.format_exc())
            log.error(error)
        except Exception:  # pylint: disable=W0703
            log.exception()
    return _impl

def dbus_handle_exceptions(func):
    """Decorator to handle exceptions, log and report them into D-Bus

    :Raises DBusException: on a firewall error code problems.
    """
    @functools.wraps(func)
    def _impl(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FirewallError as error:
            code = FirewallError.get_code(str(error))
            if code in [ errors.ALREADY_ENABLED, errors.NOT_ENABLED,
                         errors.ZONE_ALREADY_SET, errors.ALREADY_SET ]:
                log.warning(str(error))
            else:
                log.debug1(traceback.format_exc())
                log.error(str(error))
            raise FirewallDBusException(str(error))
        except DBusException as ex:
            # only log DBusExceptions once
            raise ex
        except Exception as ex:
            log.exception()
            raise FirewallDBusException(str(ex))
    # HACK: functools.wraps() does not copy the function signature and
    # dbus-python doesn't support varargs. As such we need to copy the
    # signature from the function to the newly decorated function otherwise the
    # decorators in dbus-python will manipulate the arg stack and fail
    # miserably.
    #
    # Note: This can be removed if we ever stop using dbus-python.
    #
    # Ref: https://gitlab.freedesktop.org/dbus/dbus-python/-/issues/12
    #
    _impl.__signature__ = inspect.signature(func)
    return _impl

def dbus_service_method(*args, **kwargs):
    """Add sender argument for D-Bus"""
    kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)

class dbus_service_method_deprecated:
    """Decorator that maintains a list of deprecated methods in dbus
    interfaces.
    """
    deprecated = {}

    def __init__(self, interface=None):
        self.interface = interface
        if self.interface:
            if self.interface not in self.deprecated:
                self.deprecated[self.interface] = set()

    def __call__(self, func):
        if self.interface:
            self.deprecated[self.interface].add(func.__name__)

        @functools.wraps(func)
        def _impl(*args, **kwargs):
            return func(*args, **kwargs)
        return _impl

class dbus_service_signal_deprecated(dbus_service_method_deprecated):
    """Decorator that maintains a list of deprecated signals in dbus
    interfaces.
    """
    pass
