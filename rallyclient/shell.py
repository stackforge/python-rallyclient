#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Command-line interface to the Rally API.
"""

from __future__ import print_function

import argparse
import logging
import sys

from oslo.utils import encodeutils
import six

import rallyclient
from rallyclient import exc
from rallyclient.openstack.common import cliutils


class RallyShell(object):

    def get_base_parser(self):
        parser = argparse.ArgumentParser(
            prog='rallyclient',
            description=__doc__.strip(),
            epilog='See "rallyclient help COMMAND" '
                   'for help on a specific command.',
            add_help=False,
            formatter_class=HelpFormatter,
        )

        # Global arguments
        parser.add_argument('-h', '--help',
                            action='store_true',
                            help=argparse.SUPPRESS,
                            )

        parser.add_argument('--version',
                            action='version',
                            version=rallyclient.__version__)

        parser.add_argument('-d', '--debug',
                            default=bool(cliutils.env('RALLYCLIENT_DEBUG')
                                         ),
                            action='store_true',
                            help='Defaults to env[RALLYCLIENT_DEBUG].')

        parser.add_argument('-v', '--verbose',
                            default=False, action="store_true",
                            help="Print more verbose output.")

        parser.add_argument('--timeout',
                            default=600,
                            help='Number of seconds to wait for a response.')

        parser.add_argument('--rally-url',
                            default=cliutils.env('RALLY_URL'),
                            help='Defaults to env[RALLY_URL].')

        parser.add_argument('--rally_url',
                            help=argparse.SUPPRESS)

        parser.add_argument('--rally-api-version',
                            default=cliutils.env(
                                'RALLY_API_VERSION', default='1'),
                            help='Defaults to env[RALLY_API_VERSION] '
                            'or 1.')

        parser.add_argument('--rally_api_version',
                            help=argparse.SUPPRESS)

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        # TODO(akurilin): uncomment when clientV1 will be ready
        # submodule = importutils.import_versioned_module(version, 'shell')
        # self._find_actions(subparsers, submodule)
        self._find_actions(subparsers, self)
        self._add_bash_completion_subparser(subparsers)

        return parser

    def _add_bash_completion_subparser(self, subparsers):
        subparser = subparsers.add_parser(
            'bash_completion',
            add_help=False,
            formatter_class=HelpFormatter
        )
        self.subcommands['bash_completion'] = subparser
        subparser.set_defaults(func=self.do_bash_completion)

    def _find_actions(self, subparsers, actions_module):
        for attr in (a for a in dir(actions_module) if a.startswith('do_')):
            # I prefer to be hypen-separated instead of underscores.
            command = attr[3:].replace('_', '-')
            callback = getattr(actions_module, attr)
            desc = callback.__doc__ or ''
            help = desc.strip().split('\n')[0]
            arguments = getattr(callback, 'arguments', [])

            subparser = subparsers.add_parser(command, help=help,
                                              description=desc,
                                              add_help=False,
                                              formatter_class=HelpFormatter)
            subparser.add_argument('-h', '--help', action='help',
                                   help=argparse.SUPPRESS)
            self.subcommands[command] = subparser
            for (args, kwargs) in arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=callback)

    def _setup_logging(self, debug):
        format = '%(levelname)s (%(module)s) %(message)s'
        if debug:
            logging.basicConfig(format=format, level=logging.DEBUG)
        else:
            logging.basicConfig(format=format, level=logging.WARN)
        logging.getLogger('iso8601').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    def parse_args(self, argv):
        # Parse args once to find version
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)
        self._setup_logging(options.debug)

        # build available subcommands based on version
        api_version = options.rally_api_version
        subcommand_parser = self.get_subcommand_parser(api_version)
        self.parser = subcommand_parser

        # Handle top-level --help/-h before attempting to parse
        # a command off the command line
        if options.help or not argv:
            self.do_help(options)
            return 0

        # Return parsed args
        return api_version, subcommand_parser.parse_args(argv)

    def main(self, argv):
        parsed = self.parse_args(argv)
        if parsed == 0:
            return 0
        api_version, args = parsed

        # Short-circuit and deal with help command right away.
        if args.func == self.do_help:
            self.do_help(args)
            return 0
        elif args.func == self.do_bash_completion:
            self.do_bash_completion(args)
            return 0

        # TODO(akurilin): uncomment when clientV1 will be ready
        # client = rally.get_client(api_version, **vars(args))
        # call whatever callback was selected
        # args.func(client, args)

    def do_bash_completion(self, args):
        """Prints all of the commands and options to stdout.

        The ceilometer.bash_completion script doesn't have to hard code them.
        """
        commands = set()
        options = set()
        for sc_str, sc in self.subcommands.items():
            commands.add(sc_str)
            for option in list(sc._optionals._option_string_actions):
                options.add(option)

        commands.remove('bash-completion')
        commands.remove('bash_completion')
        print(' '.join(commands | options))

    @cliutils.arg('command', metavar='<subcommand>', nargs='?',
                  help='Display help for <subcommand>')
    def do_help(self, args):
        """Display help about this program or one of its subcommands."""
        if getattr(args, 'command', None):
            if args.command in self.subcommands:
                self.subcommands[args.command].print_help()
            else:
                raise exc.CommandError("'%s' is not a valid subcommand" %
                                       args.command)
        else:
            self.parser.print_help()


class HelpFormatter(argparse.HelpFormatter):
    INDENT_BEFORE_ARGUMENTS = 6
    MAX_WIDTH_ARGUMENTS = 32

    def add_arguments(self, actions):
        for action in filter(lambda x: not x.option_strings, actions):
            for choice in action.choices:
                length = len(choice) + self.INDENT_BEFORE_ARGUMENTS
                if(length > self._max_help_position and
                           length <= self.MAX_WIDTH_ARGUMENTS):
                    self._max_help_position = length
        super(HelpFormatter, self).add_arguments(actions)

    def start_section(self, heading):
        # Title-case the headings
        heading = '%s%s' % (heading[0].upper(), heading[1:])
        super(HelpFormatter, self).start_section(heading)


def main(args=None):
    try:
        if args is None:
            args = sys.argv[1:]

        RallyShell().main(args)

    except Exception as e:
        if '--debug' in args or '-d' in args:
            raise
        else:
            print(encodeutils.safe_encode(six.text_type(e)), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
