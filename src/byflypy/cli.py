"""CLI module for ByFlyPy."""

from __future__ import annotations

import argparse
import atexit
import logging
import os.path
import sys
from collections.abc import Callable
from typing import cast

from byflypy import __version__
from byflypy.cli_parser import build_parser
from byflypy.client_factory import create_client
from byflypy.clients.api_client import ByFlyApiClient
from byflypy.clients.html_client import ByFlyHtmlClient
from byflypy.console import Console, default_console
from byflypy.database import DBManager, Table
from byflypy.models import TrafficDetails

logger = logging.getLogger(__name__)

_DEFAULT_DATABASE_FILENAME = "users.db"


def pause(console: Console | None = None) -> None:
    """Show 'press any key' prompt."""
    c = console or default_console()
    c.input("Press <Enter> to close")


def plotter_available() -> bool:
    """Return True if matplotlib/plotter is available. Result is cached on the function."""
    if getattr(plotter_available, "_available", None) is not None:
        return plotter_available._available  # type: ignore[attr-defined]
    try:
        import byflypy.plotter  # noqa: PLC0415

        plotter_available._available = getattr(byflypy.plotter, "plt", None) is not None  # type: ignore[attr-defined]
    except Exception:
        plotter_available._available = False  # type: ignore[attr-defined]
    return plotter_available._available  # type: ignore[attr-defined]


def import_plot() -> bool:
    """Try to enable plotting; print status once. Returns True if plotter is available."""
    got = plotter_available()
    if not getattr(import_plot, "_printed", False):
        import_plot._printed = True  # type: ignore[attr-defined]
        if got:
            print("Enabling plotting. Wait a few seconds...")
            print("All OK. Plotting enabled")
        else:
            print("Warning: MatPlotlib not installed - Plotting not working.")
    return got


def pass_from_db(
    login: str, db_filename: str, opt: argparse.Namespace, console: Console
) -> str | None:
    """Get password from database file."""
    try:
        db_manager = DBManager(Table(db_filename))
        res = db_manager.get_password(login)
        if res:
            opt.login = res[0]
            return res[1]
    except Exception as e:
        console.print(str(e))
    return None


def print_traffic_table(traffic: TrafficDetails, console: Console) -> None:
    """Print traffic statistics in table format."""
    console.print("\n┌─ Traffic Statistics ─────────────────────┐")
    console.print(f"│ Входящий трафик:  {traffic.total_incoming:>12.2f} Мб │")
    console.print(f"│ Исходящий трафик:  {traffic.total_outgoing:>12.2f} Мб │")
    console.print(f"│ Суммарный трафик:  {traffic.total_traffic:>12.2f} Мб │")
    console.print(f"│ Общая длительность: {traffic.total_duration:>14} │")
    console.print("└──────────────────────────────────────────┘")


class UI:
    """User interface for displaying ByFly information."""

    def __init__(
        self,
        client: ByFlyApiClient | ByFlyHtmlClient,
        console: Console | None = None,
    ) -> None:
        self._client = client
        self._console = console or default_console()
        self._is_api = getattr(client, "api_version", 1) == 2

    def print_to_console(self, s: str, end: str = "\n") -> None:
        """Print string to console."""
        self._console.print(s, end=end)

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
                    print_traffic_table(traffic, self._console)
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

    def __init__(
        self,
        console: Console | None = None,
        client_factory: Callable[
            [argparse.Namespace, str, Console],
            tuple[ByFlyApiClient | ByFlyHtmlClient | None, int | None],
        ]
        | None = None,
    ) -> None:
        self._console = console or default_console()
        self._client_factory = client_factory or create_client

    def ui(
        self,
        opt: argparse.Namespace,
        showgraph: str | None = None,
        database_filename: str = "users.db",
    ) -> int | None:
        """Output all information. Uses client factory to create authenticated client."""
        has_plot = import_plot() if opt.graph else plotter_available()

        client, err = self._client_factory(opt, database_filename, self._console)
        if err is not None:
            return err
        if client is None:
            return 2

        ui = UI(client, self._console)

        if opt.quiet:
            ui.print_info(True)
            return 0

        ui.print_info()
        ui.print_additional_info()
        ui.print_claim_payments_status()

        if opt.graph and has_plot:
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
            title = getattr(client, "info", None)
            if sessions:
                if opt.graph == "time":
                    plt.plot_time_allocation(sessions, title=title, show=show, fname=fname)
                elif opt.graph == "traf":
                    plt.plot_traf_allocation(sessions, title=title, show=show, fname=fname)

        return 0

    def setup_cmd_parser(self) -> argparse.ArgumentParser:
        """Set up command-line argument parser."""
        return build_parser()

    def interactive_mode_handler(self, opt: argparse.Namespace, database_filename: str) -> None:
        """Handle interactive mode (uses API v1: login/password prompt)."""
        try:
            opt.use_api_v1 = True  # interactive prompts for login/password only
            while True:
                a = self._console.input("Login:")
                if a == "":
                    self._console.print("Incorrect data")
                    sys.exit(1)
                opt.login = a
                a = pass_from_db(opt.login, database_filename, opt, self._console)
                if not a:
                    a = self._console.get_password("Password:")
                if a == "":
                    self._console.print("Incorrect data")
                    sys.exit(1)
                opt.password = a
                import_plot()
                if plotter_available():
                    a = self._console.input("Plot graph? [y/n]")
                    if a in ["y", "Y"]:
                        a = self._console.input("Which kind of graph [time/traf]")
                        if a == "time":
                            opt.graph = "time"
                        elif a == "traf":
                            opt.graph = "traf"
                    elif a in ["n", "N"]:
                        opt.graph = None
                self.ui(opt, database_filename=database_filename)
                while True:
                    a = self._console.input("Continue with another login [y/n]?")
                    if a == "y":
                        break
                    elif a == "n":
                        return
        except Exception as e:
            self._console.print(str(e))
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
                    self._console.print(lp[0].center(40, "*"))
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
                    self._console.print("".center(40, "*") + "\n")
        except OSError as e:
            self._console.print(str(e))

    def non_interactive_mode_handler(
        self, opt: argparse.Namespace, database_filename: str
    ) -> int | None:
        """Handle non-interactive mode. Client creation is done in ui() via factory."""
        if opt.use_api_v1 and not opt.login:
            sys.exit()
        if not opt.use_api_v1 and not opt.access_token and not opt.account_phone:
            self._console.print("Error: --account-phone is required for API v2")
            return 2
        return self.ui(opt, database_filename=database_filename)

    def main(self) -> None:
        """Main entry point for the program."""
        parser = self.setup_cmd_parser()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit()

        opt = parser.parse_args()

        log_level = logging.DEBUG if opt.debug else logging.CRITICAL
        logging.basicConfig(stream=sys.stdout, level=log_level)

        if opt.pause:
            atexit.register(pause, self._console)

        if not opt.nologo and not opt.quiet:
            self._console.print(f"version: {__version__}")

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
