"""Command-line entry point."""
import argparse
import json
import sys
from . import __version__
from .audit import audit


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = Parser(prog='presentation-generation-claim-audit')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('audit')
    command.add_argument('repo', nargs='?', default='.')
    command.add_argument('--json', action='store_true')
    command.add_argument('--verbose', action='store_true')
    command.add_argument('--ignore', action='append', default=[], metavar='PREFIX')
    command.add_argument('--fail-on', choices=('high', 'medium'), default='high')
    try:
        args = parser.parse_args(argv)
        result = audit(args.repo, args.ignore, args.fail_on)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result['verdict'])
            for finding in result['findings']:
                print(f"{finding['severity']} {finding['rule']}: {finding['message']}")
            if args.verbose:
                print(json.dumps(result, indent=2))
        return 2 if result['verdict'] == 'FAIL' else 0
    except SystemExit as error:
        return error.code
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
