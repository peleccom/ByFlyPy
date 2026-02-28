"""Command-line argument parser for ByFlyPy."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser. No business logic."""
    parser = argparse.ArgumentParser(
        description="ByFly balance checker - Check your ByFly internet account balance and statistics",
        prog="byfly",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    auth_group = parser.add_argument_group("Authentication")
    auth_token = auth_group.add_mutually_exclusive_group(required=False)
    auth_token.add_argument(
        "--account-phone",
        "--phone",
        action="store",
        type=str,
        dest="account_phone",
        help="Account phone number for API v2 (e.g., +375331234567)",
        metavar="PHONE",
    )
    auth_token.add_argument(
        "-t",
        "--access-token",
        action="store",
        type=str,
        dest="access_token",
        help="Access token for API v2 (use instead of phone/password)",
    )
    auth_group.add_argument(
        "-l",
        "--login",
        "--btk-id",
        action="store",
        type=str,
        dest="login",
        help="Login(BTK ID)",
        metavar="LOGIN",
    )
    auth_group.add_argument(
        "-p",
        "--password",
        action="store",
        type=str,
        dest="password",
        help="Password for API v1 or API v2 (will prompt if not provided)",
        metavar="PASSWORD",
    )
    auth_group.add_argument(
        "--sms-code",
        action="store",
        type=str,
        dest="sms_code",
        help="SMS 2FA code for API v2 (prompted if needed)",
        metavar="CODE",
    )
    parser.add_argument(
        "--api-v1",
        "-1",
        action="store_true",
        dest="use_api_v1",
        help="Use old HTML-based API v1 instead of API v2 (deprecated)",
    )

    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        help="Print only balance and exit",
    )
    graph_group = parser.add_argument_group("Graph Options")
    graph_group.add_argument(
        "-g",
        "--graph",
        action="store",
        dest="graph",
        type=str,
        choices=["traf", "time"],
        help="Show graph: traf (traffic allocation) or time (time allocation)",
        metavar="TYPE",
    )
    graph_group.add_argument(
        "-s",
        "--save",
        action="store",
        type=str,
        dest="imagefilename",
        help="Save graph to file (use with -g/--graph)",
        metavar="FILENAME",
    )
    output_group.add_argument(
        "--previous",
        action="store_true",
        dest="previous_period",
        help="Get statistics for previous month (use with -g/--graph)",
    )

    misc_group = parser.add_argument_group("Miscellaneous Options")
    misc_group.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        dest="interactive",
        help="Run in interactive mode (prompt for login/password)",
    )
    misc_group.add_argument(
        "--list",
        type=str,
        dest="check_list",
        metavar="FILE",
        help="Check accounts from file (format: login:password per line)",
    )
    misc_group.add_argument(
        "-d",
        "--debug",
        action="store_true",
        dest="debug",
        help="Enable debug output",
    )
    misc_group.add_argument(
        "--pause",
        action="store_true",
        dest="pause",
        help="Keep console open after execution (Windows)",
    )
    misc_group.add_argument(
        "-n",
        "--nologo",
        action="store_true",
        dest="nologo",
        help="Hide version information at startup",
    )
    misc_group.add_argument(
        "--db",
        action="store",
        type=str,
        dest="db",
        help="Path to database file for storing credentials",
        metavar="FILE",
    )

    parser.set_defaults(
        interactive=False,
        graph=None,
        imagefilename=None,
        nologo=False,
        debug=False,
        use_api_v1=False,
        sms_code=None,
        access_token=None,
        account_phone=None,
        login=None,
        password=None,
        check_list=None,
    )
    return parser
