# Copyright 2015 Canonical Ltd.
#
# This file is part of juju-wait, a juju plugin to wait for environment
# steady state.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages
setup(
    name='juju-wait',
    version='1.0',
    packages=find_packages(),
    author='Stuart Bishop',
    author_email='stuart.bishop@canonical.com',
    description='Juju plugin to wait for environment steady state',
    license='GPLv3',
    entry_points={'console_scripts': ['juju-wait = juju_wait:wait_cmd']})
