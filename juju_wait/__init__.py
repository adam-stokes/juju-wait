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
from datetime import datetime, timedelta
import json
import logging
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


def parse_ts(ts):
    '''Parse the Juju provided timestamp, which must be UTC.'''
    return datetime.strptime(ts, '%d %b %Y %H:%M:%SZ')


def run_or_die(cmd, env=None):
    try:
        # It is important we don't mix stdout and stderr, as stderr
        # will often contain SSH noise we need to ignore due to Juju's
        # lack of SSH host key handling.
        p = subprocess.Popen(cmd, universal_newlines=True, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        if p.returncode == 0:
            return out
        logging.error(err)
        logging.error("{} failed: {}".format(cmd, p.returncode))
        sys.exit(p.returncode or 43)
    except Exception as x:
        logging.error("{} failed: {}".format(x.cmd, x.returncode))
        sys.exit(x.returncode or 42)


def juju_run(unit, cmd, timeout=None):
    if timeout is None:
        timeout = 6 * 60 * 60
    return run_or_die(['juju', 'run', '--timeout={}s'.format(timeout),
                       '--unit', unit, cmd])


def get_status():
    # Older juju versions don't support --utc, so force UTC timestamps
    # using the environment variable.
    env = os.environ.copy()
    env['TZ'] = 'UTC'
    json_status = run_or_die(['juju', 'status', '--format=json'], env=env)
    if json_status is None:
        return None
    return json.loads(json_status)


def get_log_tail(unit, timeout=None):
    log = 'unit-{}.log'.format(unit.replace('/', '-'))
    cmd = 'sudo tail -1 /var/log/juju/{}'.format(log)
    return juju_run(unit, cmd, timeout=timeout)


# Juju 1.24+ provides us with the timestamp the status last changed.
# If all units are idle more than this many seconds, the system is
# quiescent. This may be unnecessary, but protects against races
# where all units report they are currently idle but there are hooks
# still due to be run.
IDLE_CONFIRMATION = timedelta(seconds=5)


def wait_cmd(args=sys.argv[1:]):
    description = dedent("""\
        Wait for environment steady state.

        The environment is considered in a steady state once all hooks
        have completed running and there are no hooks queued to run,
        on all units.

        If you need a timeout, use the timeout(1) tool.
        """)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-e', '--environment', metavar="ENV", type=str,
                        action=EnvironmentAction, nargs=1)
    parser.add_argument('--description', action=DescriptionAction, nargs=0)
    parser.add_argument('-q', '--quiet', dest='quiet',
                        action='store_true', default=False)
    parser.add_argument('-v', '--verbose', dest='verbose',
                        action='store_true', default=False)
    args = parser.parse_args(args)

    # Parser did not exit, so continue.
    logging.basicConfig()
    log = logging.getLogger()
    if args.quiet:
        log.setLevel(logging.WARN)
    elif args.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    return wait(log)


def wait(log):
    # pre-juju 1.24, we can only detect idleless by looking for changes
    # in the logs.
    prev_logs = {}

    while True:
        status = get_status()
        ready = True

        all_units = set()

        # Units with started agents that are not dying.
        live_units = set()

        # 'ready' units are up, and might be idle. They need to have their
        # logs sniffed because they are running Juju 1.23 or earlier.
        ready_units = set()

        # 'idle' units are known idle, and have remained idle for a short
        # while. These units are Juju 1.24 or later.
        idle_units = set()

        # Log storage to compare with prev_logs.
        logs = {}

        for sname, service in status.get('services', {}).items():
            if service.get('life') in ('dying', 'dead'):
                logging.debug('{} is dying'.format(sname))
                ready = False

            for uname, unit in service.get('units', {}).items():
                all_units.add(uname)
                alive = unit.get('life') not in ('dying', 'dead')
                started = unit.get('agent-state') == 'started'
                state = unit.get('agent-status', {}).get('current')
                since = parse_ts(unit.get('agent-status', {}).get('since'))
                if alive and started:
                    live_units.add(uname)
                    if state is not None:
                        # Juju 1.24+
                        now = datetime.now()
                        if state == 'idle':
                            if since + IDLE_CONFIRMATION < now:
                                logging.debug('{} idle since {}'
                                              ''.format(uname, since))
                                idle_units.add(uname)
                            else:
                                logging.debug('{} might be idle'.format(uname))
                        else:
                            logging.debug('{} is {} since {}'
                                          ''.format(uname, state, since))
                    else:
                        ready_units.add(uname)
                else:
                    ready = False
                    agent_state = unit.get('agent-state')
                    if agent_state == 'error':
                        info = unit.get('agent-state-info')
                        logging.error("{} failed: {}".format(uname, info))
                        sys.exit(1)
                    else:
                        logging.debug('{} is {}'.format(uname, agent_state))

        if ready and ready_units:
            # For Juju 1.23 or earlier agents, we need to fallback to
            # old behavior. We use juju run to grab the log tail on all
            # units. If the logs are identical twice in a row,
            # we know that hooks have stopped running. This is fragile,
            # as enabling extra Juju logging may break this.
            for uname in ready_units:
                logs[uname] = get_log_tail(uname)
                if logs[uname] == prev_logs.get(uname):
                    logging.debug('{} is idle - no hook activity'
                                  ''.format(uname))
                    idle_units.add(uname)
                elif prev_logs.get(uname):
                    logging.debug('{} is active. {}'.format(uname,
                                                            logs[uname]))
            prev_logs = logs

        # If there is nothing but idle units, then we are good to go.
        if ready and all_units == idle_units:
            logging.info('All units idle ({})'.format(', '.join(idle_units)))
            return

        time.sleep(2)


if __name__ == '__main__':
    # I use these to launch the entry points from the source tree.
    # Most installations will be using the setuptools generated
    # launchers.
    script = os.path.basename(sys.argv[0])
    if script == 'juju-wait':
        wait_cmd()
    else:
        raise RuntimeError('Unknown script {}'.format(script))
