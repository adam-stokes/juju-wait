#!/usr/bin/python3

# This file is part of juju-wait, a juju plugin to wait for environment
# steady state.
#
# Copyright 2015 Canonical Ltd.
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

import argparse
import json
import os
import subprocess
import sys
from textwrap import dedent
import time


class DescriptionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        parser.exit(0, parser.description.splitlines()[0] + '\n')


class EnvironmentAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        os.environ['JUJU_ENV'] = values[0]


def run_or_die(cmd):
    try:
        p = subprocess.Popen(cmd, universal_newlines=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        if p.returncode == 0:
            return out
        print(err, file=sys.stderr)
        print("{} failed: {}".format(cmd, p.returncode), file=sys.stderr)
        sys.exit(p.returncode or 43)
    except Exception as x:
        print("{} failed: {}".format(x.cmd, x.returncode), file=sys.stderr)
        sys.exit(x.returncode or 42)


def juju_run(unit, cmd, timeout=None):
    if timeout is None:
        timeout = 6 * 60 * 60
    return run_or_die(['juju', 'run', '--timeout={}s'.format(timeout),
                       '--unit', unit, cmd])


def get_status():
    json_status = run_or_die(['juju', 'status', '--format=json'])
    if json_status is None:
        return None
    return json.loads(json_status)


def get_log_tail(unit, timeout=None):
    log = 'unit-{}.log'.format(unit.replace('/', '-'))
    cmd = 'sudo tail -1 /var/log/juju/{}'.format(log)
    return juju_run(unit, cmd, timeout=timeout)


def wait_cmd(args=sys.argv[1:]):
    description = dedent("""\
        Wait for environment steady state.

        The environment is considered in a steady state once all hooks
        have completed running and there are no hooks queued to run,
        on all units.

        This plugin accepts no arguments apart from '-e' to ensure
        compatibility when this command is provided built in to juju.
        If you need a timeout, use the timeout(1) tool.
        """)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-e', '--environment', metavar="ENV", type=str,
                        action=EnvironmentAction, nargs=1)
    parser.add_argument('--description', action=DescriptionAction, nargs=0)
    args = parser.parse_args(args)

    prev_logs = []
    while True:
        status = get_status()
        ready = True
        ready_units = set()
        logs = []

        for service in status.get('services', {}).values():
            if service.get('life') in ('dying', 'dead'):
                ready = False

            for uname, unit in service.get('units', {}).items():
                alive = unit.get('life') not in ('dying', 'dead')
                started = unit.get('agent-state') == 'started'
                if alive and started:
                    ready_units.add(uname)
                else:
                    failed = unit.get('agent-state') == 'error'
                    if failed:
                        info = unit.get('agent-state-info')
                        print("{} failed: {}".format(uname, info),
                              file=sys.stderr)
                        sys.exit(1)
                    ready = False

        if ready:
            logs = list(map(get_log_tail, sorted(ready_units)))
            if logs == prev_logs:
                # If all units are in a good state and the logs are
                # unchanged, we are done waiting.
                break
            else:
                prev_logs = logs
        else:
            prev_logs = []
        time.sleep(1)


if __name__ == '__main__':
    # I use these to launch the entry points from the source tree.
    # Most installations will be using the setuptools generated
    # launchers.
    script = os.path.basename(sys.argv[0])
    if script == 'juju-wait':
        wait_cmd()
    else:
        raise RuntimeError('Unknown script {}'.format(script))
