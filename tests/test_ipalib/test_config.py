# Authors:
#   Martin Nagy <mnagy@redhat.com>
#
# Copyright (C) 2008  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""
Test the `ipalib.config` module.
"""

import types

from tests.util import raises, setitem, delitem, ClassChecker
from tests.util import getitem, setitem, delitem
from ipalib import config


def test_Environment():
    """
    Test the `ipalib.config.Environment` class.
    """
    # This has to be the same as iter_cnt
    control_cnt = 0
    class prop_class:
        def __init__(self, val):
            self._val = val
        def get_value(self):
            return self._val

    class iter_class(prop_class):
        # Increment this for each time iter_class yields
        iter_cnt = 0
        def get_value(self):
            for item in self._val:
                self.__class__.iter_cnt += 1
                yield item

    # Tests for basic functionality
    basic_tests = (
        ('a', 1),
        ('b', 'basic_foo'),
        ('c', ('basic_bar', 'basic_baz')),
    )
    # Tests with prop classes
    prop_tests = (
        ('d', prop_class(2), 2),
        ('e', prop_class('prop_foo'), 'prop_foo'),
        ('f', prop_class(('prop_bar', 'prop_baz')), ('prop_bar', 'prop_baz')),
    )
    # Tests with iter classes
    iter_tests = (
        ('g', iter_class((3, 4, 5)), (3, 4, 5)),
        ('h', iter_class(('iter_foo', 'iter_bar', 'iter_baz')),
                         ('iter_foo', 'iter_bar', 'iter_baz')
        ),
    )

    # Set all the values
    env = config.Environment()
    for name, val in basic_tests:
        env[name] = val
    for name, val, dummy in prop_tests:
        env[name] = val
    for name, val, dummy in iter_tests:
        env[name] = val

    # Test if the values are correct
    for name, val in basic_tests:
        assert env[name] == val
    for name, dummy, val in prop_tests:
        assert env[name] == val
    # Test if the get_value() function is called only when needed
    for name, dummy, correct_values in iter_tests:
        values_in_env = []
        for val in env[name]:
            control_cnt += 1
            assert iter_class.iter_cnt == control_cnt
            values_in_env.append(val)
        assert tuple(values_in_env) == correct_values

    # Test __setattr__()
    env.spam = 'ham'

    assert env.spam == 'ham'
    assert env['spam'] == 'ham'
    assert env.get('spam') == 'ham'
    assert env.get('nonexistent') == None
    assert env.get('nonexistent', 42) == 42

    # Test if we throw AttributeError exception when trying to overwrite
    # existing value, or delete it
    raises(AttributeError, setitem, env, 'a', 1)
    raises(AttributeError, setattr, env, 'a', 1)
    raises(AttributeError, delitem, env, 'a')
    raises(AttributeError, delattr, env, 'a')
    raises(AttributeError, config.Environment.update, env, dict(a=1000))
    # This should be silently ignored
    env.update(dict(a=1000), True)
    assert env.a != 1000


class test_Env(ClassChecker):
    """
    Test the `ipalib.config.Env` class.
    """

    _cls = config.Env

    def test_init(self):
        """
        Test the `ipalib.config.Env.__init__` method.
        """
        o = self.cls()

    def test_lock(self):
        """
        Test the `ipalib.config.Env.__lock__` method.
        """
        o = self.cls()
        assert o._Env__locked is False
        o.__lock__()
        assert o._Env__locked is True
        e = raises(StandardError, o.__lock__)
        assert str(e) == 'Env.__lock__() already called'

    def test_getattr(self):
        """
        Test the `ipalib.config.Env.__getattr__` method.

        Also tests the `ipalib.config.Env.__getitem__` method.
        """
        o = self.cls()
        value = 'some value'
        o.key = value
        assert o.key is value
        assert o['key'] is value
        o.call = lambda: 'whatever'
        assert o.call == 'whatever'
        assert o['call'] == 'whatever'
        for name in ('one', 'two'):
            e = raises(AttributeError, getattr, o, name)
            assert str(e) == 'Env.%s' % name
            e = raises(KeyError, getitem, o, name)
            assert str(e) == repr(name)

    def test_setattr(self):
        """
        Test the `ipalib.config.Env.__setattr__` method.

        Also tests the `ipalib.config.Env.__setitem__` method.
        """
        items = [
            ('one', 1),
            ('two', lambda: 2),
            ('three', 3),
            ('four', lambda: 4),
        ]
        for setvar in (setattr, setitem):
            o = self.cls()
            for (i, (name, value)) in enumerate(items):
                setvar(o, name, value)
                assert getattr(o, name) == i + 1
                assert o[name] == i + 1
                if callable(value):
                    assert name not in dir(o)
                else:
                    assert name in dir(o)
                e = raises(AttributeError, setvar, o, name, 42)
                assert str(e) == 'cannot overwrite Env.%s with 42' % name
            o = self.cls()
            o.__lock__()
            for (name, value) in items:
                e = raises(AttributeError, setvar, o, name, value)
                assert str(e) == \
                    'locked: cannot set Env.%s to %r' % (name, value)

    def test_delattr(self):
        """
        Test the `ipalib.config.Env.__delattr__` method.

        This also tests that ``__delitem__`` is not implemented.
        """
        o = self.cls()
        o.one = 1
        assert o.one == 1
        for key in ('one', 'two'):
            e = raises(AttributeError, delattr, o, key)
            assert str(e) == 'cannot del Env.%s' % key
            e = raises(AttributeError, delitem, o, key)
            assert str(e) == '__delitem__'

    def test_contains(self):
        """
        Test the `ipalib.config.Env.__contains__` method.
        """
        o = self.cls()
        items = [
            ('one', 1),
            ('two', lambda: 2),
            ('three', 3),
            ('four', lambda: 4),
        ]
        for (key, value) in items:
            assert key not in o
            o[key] = value
            assert key in o

    def test_iter(self):
        """
        Test the `ipalib.config.Env.__iter__` method.
        """
        o = self.cls()
        assert list(o) == []
        keys = ('one', 'two', 'three', 'four', 'five')
        for key in keys:
            o[key] = 'the value'
        assert list(o) == sorted(keys)


def test_set_default_env():
    """
    Test the `ipalib.config.set_default_env` function.
    """

    # Make sure we don't overwrite any properties
    d = dict(
        query_dns = False,
        server = ('first', 'second'),
        realm = 'myrealm',
        # test right conversions
        server_context = 'off',
    )
    env = config.Environment()
    config.set_default_env(env)
    env.update(d)
    assert env['server_context'] == False
    assert env['query_dns'] == False

    # Make sure the servers is overwrote properly (that it is still LazyProp)
    iter = env['server']
    assert iter.next() == 'first'
    assert iter.next() == 'second'


def test_LazyProp():
    """
    Test the `ipalib.config.LazyProp` class.
    """

    def dummy():
        return 1

    # Basic sanity testing with no initial value
    prop = config.LazyProp(int, dummy)
    assert prop.get_value() == 1
    prop.set_value(2)
    assert prop.get_value() == 2

    # Basic sanity testing with initial value
    prop = config.LazyProp(int, dummy, 3)
    assert prop.get_value() == 3
    prop.set_value(4)
    assert prop.get_value() == 4


def test_LazyIter():
    """
    Test the `ipalib.config.LazyIter` class.
    """

    def dummy():
        yield 1
        yield 2

    # Basic sanity testing with no initial value
    prop = config.LazyIter(int, dummy)
    iter = prop.get_value()
    assert iter.next() == 1
    assert iter.next() == 2
    raises(StopIteration, iter.next)

    # Basic sanity testing with initial value
    prop = config.LazyIter(int, dummy, 0)
    iter = prop.get_value()
    assert iter.next() == 0
    assert iter.next() == 1
    assert iter.next() == 2
    raises(StopIteration, iter.next)


def test_read_config():
    """
    Test the `ipalib.config.read_config` class.
    """

    raises(AssertionError, config.read_config, 1)
