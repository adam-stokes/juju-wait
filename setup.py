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
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='juju-wait',
    version='2.3.1',
    packages=find_packages(),
    author='Stuart Bishop',
    author_email='stuart.bishop@canonical.com',
    description='Juju plugin to wait for environment steady state',
    url='https://launchpad.net/juju-wait',
    long_description=long_description,
    license='GPLv3',
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Environment :: Plugins',
                 'Intended Audience :: Developers',
                 'Intended Audience :: System Administrators',
                 'License :: OSI Approved '
                 ':: GNU General Public License v3 (GPLv3)',
                 'Operating System :: OS Independent',
                 'Topic :: System :: Installation/Setup',
                 'Topic :: Utilities',
                 'Programming Language :: Python :: 3'],
    keywords='juju',
    install_requires=['psutil'],
    entry_points={'console_scripts': ['juju-wait = juju_wait:wait_cmd']})
