"""CLI module for ByFlyPy."""

from __future__ import annotations

import argparse
import atexit
import getpass
import logging
import os.path
import sys
from typing import cast

from byflypy import __version__
from byflypy.clients import html_client
from byflypy.clients.api_client import ByFly2FARequiredError, ByFlyApiClient, TokenManager
from byflypy.clients.html_client import ByFlyError, ByFlyHtmlClient, get_exception_str
from byflypy.database import DBManager, Table
from byflypy.models import TrafficDetails

logger = logging.getLogger(__name__)

_DEFAULT_DATABASE_FILENAME = "users.db"
HAS_MATPLOT = False


def pause() -> None:
    """Show 'press any key' prompt."""
    input("Press <Enter> to close")


def import_plot() -> None:
    """Import plotter module if available."""
    global HAS_MATPLOT
    if not HAS_MATPLOT:
        try:
            print("Enabling plotting. Wait a few seconds...")

            print("All OK. Plotting enabled")
            HAS_MATPLOT = True
        except Exception:
            print("Warning: MatPlotlib not installed - Plotting not working.")


def pass_from_db(login: str, db_filename: str, opt: argparse.Namespace) -> str | None:
    """Get password from database file."""
    try:
        db_manager = DBManager(Table(db_filename))
        res = db_manager.get_password(login)
        if res:
            opt.login = res[0]
            return res[1]
    except Exception as e:
        print(e)
    return None


def print_traffic_table(traffic: TrafficDetails) -> None:
    """Print traffic statistics in table format."""
    print("\n┌─ Traffic Statistics ─────────────────────┐")
    print(f"│ Входящий трафик:  {traffic.total_incoming:>12.2f} Мб │")
    print(f"│ Исходящий трафик:  {traffic.total_outgoing:>12.2f} Мб │")
    print(f"│ Суммарный трафик:  {traffic.total_traffic:>12.2f} Мб │")
    print(f"│ Общая длительность: {traffic.total_duration:>14} │")
    print("└──────────────────────────────────────────┘")


class UI:
    """User interface for displaying ByFly information."""

    def __init__(self, client: ByFlyApiClient | ByFlyHtmlClient) -> None:
        self._client = client
        # Determine client type by checking class name
        # This is more reliable than isinstance with mocked objects
        client_class_name = type(client).__name__
        self._is_api = client_class_name == "ByFlyApiClient" or client_class_name.endswith(
            "ByFlyApiClient"
        )

    def print_to_console(self, s: str, end: str = "\n") -> None:
        """Print string to console."""
        print(s, end=end)

    def print_info(self, only_balance: bool = False) -> bool:
        """Get and print account information."""
        if self._is_api:
            return self._print_info_api(only_balance)
        return self._print_info_html(only_balance)

    def _print_info_html(self, only_balance: bool = False) -> bool:
        """Print info from legacy HTML API."""
        client = cast(ByFlyHtmlClient, self._client)
        info = client.get_account_info_page()
        if not info:
            return False
        if only_balance:
            self.print_to_console(f"{info.balance}", end="")
            return True
        self.print_to_console(
            f"Абонент - {info.full_name}\n"
            f"Тариф   - {info.plan}\n"
            f"Баланс  - {info.balance} {client.get_money_measure()}"
        )
        return True

    def _print_info_api(self, only_balance: bool = False) -> bool:
        """Print info from new REST API."""
        client = cast(ByFlyApiClient, self._client)
        contract = client.get_primary_contract()
        if not contract:
            return False

        if only_balance:
            self.print_to_console(f"{contract.balance}", end="")
            return True

        app = contract.applications[0] if contract.applications else None
        tariff_name = app.tariff.name if app and app.tariff else "Неизвестно"
        terminate_info = ""
        if contract.terminate_in is not None:
            terminate_info = f"\nСрок действия тарифа: {contract.terminate_in} дн."

        self.print_to_console(
            f"Абонент - {contract.name}\n"
            f"Тариф   - {tariff_name}\n"
            f"Баланс  - {contract.balance} byn{terminate_info}"
        )
        return True

    def print_additional_info(self) -> bool:
        """Print additional statistics information."""
        if self._is_api:
            return self._print_additional_info_api()
        return self._print_additional_info_html()

    def _print_additional_info_html(self) -> bool:
        """Print additional info from legacy API."""
        client = cast(ByFlyHtmlClient, self._client)
        total_stat_info = client.get_additional_info()
        if total_stat_info:
            s = (
                f"Суммарный трафик - {total_stat_info.total_traf} {client.get_traf_measure()}\n"
                f"Превышение стоимости - {total_stat_info.total_cost} {client.get_money_measure()}"
            )
            self.print_to_console(s)
            return True
        return False

    def _print_additional_info_api(self) -> bool:
        """Print additional info from new API."""
        client = cast(ByFlyApiClient, self._client)
        contract = client.get_primary_contract()
        if not contract:
            return False

        # Get traffic details for first internet application
        for app in contract.applications:
            try:
                traffic = client.get_traffic_details(contract.id, app.id)
                if traffic:
                    print_traffic_table(traffic)
                    return True
            except Exception as e:
                logger.debug(f"Failed to get traffic for app {app.id}: {e}")
                continue

        return False

    def print_claim_payments_status(self) -> None:
        """Print active claim payment information."""
        if self._is_api:
            self._print_claim_payments_api()
        else:
            self._print_claim_payments_html()

    def _print_claim_payments_html(self) -> None:
        """Print claim payments from legacy API."""
        client = cast(ByFlyHtmlClient, self._client)
        payments = client.get_payments_page()
        for payment in payments:
            if payment.is_active:
                self.print_to_console(
                    f"Обещанный платеж от {payment.date} на сумму {payment.cost} "
                    f"{client.get_money_measure()}"
                )
                break

    def _print_claim_payments_api(self) -> None:
        """Print claim payments info from new API."""
        client = cast(ByFlyApiClient, self._client)
        contract = client.get_primary_contract()
        if not contract:
            return

        if contract.can_apply_promised_payment:
            max_amount = contract.max_promised_payment_amount
            amount_str = f" до {max_amount}" if max_amount else ""
            self.print_to_console(f"Обещанный платеж доступен{amount_str}")

    def get_sessions(self, previous_period: bool = False) -> list:
        """Get sessions for plotting."""
        if self._is_api:
            return self._get_sessions_api(previous_period)
        else:
            return cast(ByFlyHtmlClient, self._client).get_log(previous_period=previous_period)

    def _get_sessions_api(self, previous_period: bool = False) -> list:
        """Get sessions from API for plotting."""
        client = cast(ByFlyApiClient, self._client)
        contract = client.get_primary_contract()
        if not contract:
            return []

        # Get traffic details for first application with sessions
        for app in contract.applications:
            try:
                traffic = client.get_traffic_details(contract.id, app.id)
                if traffic and traffic.sessions:
                    return traffic.sessions
            except Exception as e:
                logger.debug(f"Failed to get traffic for app {app.id}: {e}")
                continue
        return []


class Program:
    """Main program class for ByFly balance checker."""

    def ui(self, opt: argparse.Namespace, showgraph: str | None = None) -> int | None:
        """Output all information."""
        if opt.graph:
            import_plot()

        if opt.use_api_v1:
            client = ByFlyHtmlClient(opt.login, opt.password)
            ui = UI(client)
            try:
                client.login()
            except ByFlyError as e:
                print(get_exception_str(e))
                return 2

            if opt.quiet:
                ui.print_info(True)
                return 0

            ui.print_info()
            ui.print_additional_info()
            ui.print_claim_payments_status()

            if opt.graph and HAS_MATPLOT:
                from byflypy.plotter import Plotter  # noqa: PLC0415

                plt = Plotter()
                if opt.imagefilename:
                    fname = opt.imagefilename
                    show = False
                else:
                    show = True
                    fname = None
                if showgraph == "always":
                    show = True
                if opt.graph == "time":
                    plt.plot_time_allocation(
                        client.get_log(previous_period=opt.previous_period),
                        title=client.info,
                        show=show,
                        fname=fname,
                    )
                elif opt.graph == "traf":
                    plt.plot_traf_allocation(
                        client.get_log(previous_period=opt.previous_period),
                        title=client.info,
                        show=show,
                        fname=fname,
                    )

            return 0

        # API v2 path
        phone = None

        # Normalize phone number (add + prefix if not present)
        phone = self._normalize_phone(opt)

        # Use token from command line, file, or login
        if opt.access_token:
            client = ByFlyApiClient(
                phone=opt.account_phone, password=None, sms_code=None, login=opt.login
            )
            client.set_access_token(opt.access_token)
        elif phone:
            token_manager = TokenManager()
            if not token_manager.load(phone) and not opt.password:
                opt.password = self._get_password_if_not_specified(opt.password)
            client = ByFlyApiClient(
                phone=phone,
                password=opt.password,
                sms_code=opt.sms_code,
                login=opt.login,
                token_manager=token_manager,
            )

            try:
                client.login()
            except ByFly2FARequiredError:
                code = input("Enter SMS code from phone: ")
                if not code:
                    return 2
                client.set_sms_code(code)
                try:
                    client.login()
                except ByFly2FARequiredError:
                    print("Invalid or expired SMS code")
                    return 2
            except ByFlyError as e:
                print(get_exception_str(e))
                return 2

            print(f"Access token: {client.access_token}")
        else:
            print("Error: --account-phone or --access-token is required for API v2")
            return 2

        # If --btk-id specified, validate it exists and set the contract
        if opt.login:
            contracts = client.get_contracts()
            btk_ids = []
            for contract in contracts:
                btk_ids.append(contract.btk_id)
                if contract.btk_id == opt.login:
                    client._login = contract.login
            if not client._login:
                print(f"Error: Btk ID '{opt.login}' not found for this account")
                print(f"Available Btk IDs: {', '.join(btk_ids)}")
                return 2

        # If --btk-id not specified, list all available Btk IDs and ask user to specify
        if not opt.login:
            contracts = client.get_contracts()
            btk_entries = [(c.btk_id, c.name, c.balance, c.login) for c in contracts if c.btk_id]

            if len(btk_entries) == 0:
                print("Error: No internet logins found for this account")
                return 2
            elif len(btk_entries) == 1:
                opt.login = btk_entries[0][0]
                client._login = btk_entries[0][3]
            else:
                print("Available internet logins (Btk ID):")
                for btk_id, name, balance, _ in btk_entries:
                    print(f"  - {btk_id}: {name} (balance: {balance})")
                print("\nPlease specify one with --login")
                return 2

        ui = UI(client)

        if opt.quiet:
            ui.print_info(True)
            return 0

        ui.print_info()
        ui.print_additional_info()
        ui.print_claim_payments_status()

        if opt.graph and HAS_MATPLOT:
            from byflypy.plotter import Plotter  # noqa: PLC0415

            plt = Plotter()
            if opt.imagefilename:
                fname = opt.imagefilename
                show = False
            else:
                show = True
                fname = None
            if showgraph == "always":
                show = True
            sessions = ui.get_sessions(previous_period=opt.previous_period)
            if sessions:
                if opt.graph == "time":
                    plt.plot_time_allocation(sessions, show=show, fname=fname)
                elif opt.graph == "traf":
                    plt.plot_traf_allocation(sessions, show=show, fname=fname)

        return 0

    def _normalize_phone(self, opt):
        phone = opt.account_phone
        if phone and not phone.startswith("+"):
            phone = "+" + phone
        return phone

    def _get_password_if_not_specified(self, password):
        if not password:
            password = getpass.getpass("Password:", echo_char="*")  # type: ignore[unknown-argument]
        return password

    def setup_cmd_parser(self) -> argparse.ArgumentParser:
        """Set up command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="ByFly balance checker - Check your ByFly internet account balance and statistics",
            prog="byfly",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        auth_group = parser.add_argument_group("Authentication")
        auth_token = auth_group.add_mutually_exclusive_group(required=False)
        auth_token.add_argument(
            "-t",
            "--access-token",
            action="store",
            type=str,
            dest="access_token",
            help="Access token for API v2 (use instead of phone/password)",
        )
        auth_token.add_argument(
            "--account-phone",
            "--phone",
            action="store",
            type=str,
            dest="account_phone",
            help="Account phone number for API v2 (e.g., +375331234567)",
            metavar="PHONE",
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

        api_v1_group = parser.add_argument_group("Authentication (API v1 - Legacy/Deprecated)")
        api_v1_group.add_argument(
            "-l",
            "--login",
            "--btk-id",
            action="store",
            type=str,
            dest="login",
            help="Login(BTK ID) for API v1 (legacy)",
            metavar="LOGIN",
        )

        parser.add_argument(
            "--api-v1",
            "-1",
            action="store_true",
            dest="use_api_v1",
            help="Use old HTML-based API v1 instead of API v2 (deprecated)",
        )

        contract_group = parser.add_argument_group("Contract Selection (API v2)")
        contract_group.add_argument(
            "--sms-code",
            action="store",
            type=str,
            dest="sms_code",
            help="SMS 2FA code for API v2 (prompted if needed)",
            metavar="CODE",
        )

        output_group = parser.add_argument_group("Output Options")
        output_group.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            dest="quiet",
            help="Print only balance and exit",
        )
        output_group.add_argument(
            "-g",
            "--graph",
            action="store",
            dest="graph",
            type=str,
            choices=["traf", "time"],
            help="Show graph: traf (traffic allocation) or time (time allocation)",
            metavar="TYPE",
        )
        output_group.add_argument(
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

    def interactive_mode_handler(self, opt: argparse.Namespace, database_filename: str) -> None:
        """Handle interactive mode (uses API v1: login/password prompt)."""
        try:
            opt.use_api_v1 = True  # interactive prompts for login/password only
            while True:
                a = input("Login:")
                if a == "":
                    print("Incorrect data")
                    sys.exit(1)
                opt.login = a
                a = pass_from_db(opt.login, database_filename, opt)
                a = self._get_password_if_not_specified(a)
                if a == "":
                    print("Incorrect data")
                    sys.exit(1)
                opt.password = a
                import_plot()
                if HAS_MATPLOT:
                    a = input("Plot graph? [y/n]")
                    if a in ["y", "Y"]:
                        a = input("Which kind of graph [time/traf]")
                        if a == "time":
                            opt.graph = "time"
                        elif a == "traf":
                            opt.graph = "traf"
                    elif a in ["n", "N"]:
                        opt.graph = None
                self.ui(opt)
                while True:
                    a = input("Continue with another login [y/n]?")
                    if a == "y":
                        break
                    elif a == "n":
                        return
        except Exception as e:
            print(e)
            sys.exit(1)

    def list_checker_handler(self, opt: argparse.Namespace) -> None:
        """Handle list checker mode (file format login:password = API v1)."""
        try:
            opt.use_api_v1 = True  # list file is login:password format
            with open(opt.check_list) as list_file:
                for line in list_file:
                    lp = line.strip().partition(":")
                    if lp[2] == "":
                        continue
                    print(lp[0].center(40, "*"))
                    opt.login = lp[0]
                    opt.password = lp[2]
                    if opt.imagefilename:
                        fname = opt.imagefilename
                        basename = os.path.basename(fname)
                        no_ext = basename.partition(".")[0]
                        fname = fname.replace(no_ext, lp[0])
                    else:
                        fname = None
                    opt.imagefilename = fname
                    self.ui(opt)
                    print("".center(40, "*") + "\n")
        except OSError as e:
            print(f"{e}")

    def non_interactive_mode_handler(
        self, opt: argparse.Namespace, database_filename: str
    ) -> int | None:
        """Handle non-interactive mode."""
        if opt.use_api_v1:
            if not opt.login:
                sys.exit()
            if not opt.password:
                opt.password = pass_from_db(opt.login, database_filename, opt)
                opt.password = self._get_password_if_not_specified(opt.password)
        else:
            # For API v2, we need account_phone and password
            if not opt.access_token and not opt.account_phone:
                print("Error: --account-phone is required for API v2")
                return 2
        return self.ui(opt)

    def main(self) -> None:
        """Main entry point for the program."""
        parser = self.setup_cmd_parser()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit()

        opt = parser.parse_args()

        # Set debug mode for html_client
        html_client._DEBUG_ = opt.debug
        log_level = logging.DEBUG if opt.debug else logging.CRITICAL
        logging.basicConfig(stream=sys.stdout, level=log_level)

        if opt.pause:
            atexit.register(pause)

        if not opt.nologo and not opt.quiet:
            print(f"version: {__version__}")

        database_filename = opt.db if opt.db else _DEFAULT_DATABASE_FILENAME

        if opt.interactive:
            self.interactive_mode_handler(opt, database_filename)
        elif opt.check_list:
            self.list_checker_handler(opt)
        else:
            result_code = self.non_interactive_mode_handler(opt, database_filename)
            if result_code is not None:
                sys.exit(result_code)


def main() -> None:
    """Entry point for command-line usage."""
    Program().main()


if __name__ == "__main__":
    main()
