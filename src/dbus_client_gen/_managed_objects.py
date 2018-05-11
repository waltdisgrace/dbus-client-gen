# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Code for generating classes suitable for wrapping a table for an object
returned by GetManagedObjects().
"""

import types

from ._errors import DbusClientGenerationError
from ._errors import DbusClientRuntimeError


def managed_object_builder(spec):
    """
    Returns a function that builds a method interface based on 'spec'.
    This method interface is a simple one to return the values of
    properties from a table generated by a GetManagedObjects() method call
    for the object that implements the given interface.

    Usage example:

    * spec is an xml specification for an interface in the format returned
    by the Introspect() method.
    * table is the dict associated with a particular object returned by the
    GetManagedObjects() method.

    >>> builder = gmo_reader_builder(spec)
    >>> Filesystem = types.new_class("Filesystem", bases=(object,), exec_body=builder)
    >>> fs = Filesystem(table)
    >>> fs.Pool()

    :param spec: the interface specification
    :type spec: Element
    """

    try:
        interface_name = spec.attrib['name']
    except KeyError as err:  # pragma: no cover
        raise DbusClientGenerationError(
            "No name attribute found for interface.") from err

    def build_property(name):
        """
        Build a single property getter for this class.

        :param str name: the property name

        :returns: the value of the property
        :rtype: object
        """

        def dbus_func(self):
            """
            The property getter.
            """
            try:
                # pylint: disable=protected-access
                return self._table[name]
            except KeyError as err:
                raise DbusClientRuntimeError(
                    "No entry found for interface %s and property %s" %
                    (interface_name, name), interface_name) from err

        return dbus_func

    def builder(namespace):
        """
        The property class's namespace.

        :param namespace: the class's namespace
        """
        for prop in spec.findall('./property'):
            try:
                name = prop.attrib['name']
            # Should not fail if introspection data is well formed.
            except KeyError as err:  # pragma: no cover
                fmt_str = ("No name attribute found for some property "
                           "belonging to interface \"%s\"")
                raise DbusClientGenerationError(
                    fmt_str % interface_name) from err

            namespace[name] = build_property(name)

        def __init__(self, table):
            """
            The initalizer for this class.
            """
            if interface_name not in table:
                raise DbusClientRuntimeError(
                    "Object does not implement interface %s" % interface_name,
                    interface_name)
            # pylint: disable=protected-access
            self._table = table[interface_name]

        namespace['__init__'] = __init__

    return builder


def managed_object_class(name, spec):
    """
    Returns a class with an __init__ function which takes one
    argument, a table which is a portion of the tree returned by
    ObjectManager.GetManagedObjects(). The constructed object contains
    a set of methods for directly accessing the properties which are stored
    in the table.

    Usage example:

    * spec is an XML specification for an interface in the format returned
    by the Introspect() method.
    * table is the dict associated with a particular object returned by the
    GetManagedObjects() method.

    >>> Filesystem = managed_object_class("Filesystem", spec)
    >>> fs = Filesystem(table)
    >>> fs.Pool()

    :param str name: the name to give the auto-generated class
    :param spec: the interface specification
    :rtype: type
    """
    return types.new_class(
        name, bases=(object, ), exec_body=managed_object_builder(spec))
