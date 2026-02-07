"""ByFly balance checker and statistics viewer."""

import argparse
import atexit
import getpass
import logging
import sys
from typing import Optional

import byflyuser

__VERSION__ = "3.1"
__FIGURE_FORMATS__ = ["png", "pdf", "svg", "eps", "ps"]

_DEFAULT_DATABASE_FILENAME = "users.db"
HAS_MATPLOT = False

logger = logging.getLogger(__name__)
plotinfo = None


def pause() -> None:
    """Show 'press any key' prompt."""
    input("Press <Enter> to close")


def import_plot() -> None:
    """Import plotinfo module if available."""
    global plotinfo, HAS_MATPLOT
    if "plotinfo" not in sys.modules:
        try:
            print("Enabling plotting. Wait a few seconds...")
            import plotinfo

            print("All OK. Plotting enabled")
            HAS_MATPLOT = True
        except Exception:
            print("Warning: MatPlotlib not installed - Plotting not working.")


def pass_from_db(login: str, db_filename: str, opt: argparse.Namespace) -> Optional[str]:
    """Get password from database file.

    Args:
        login: Username to look up
        db_filename: Path to database file
        opt: Options namespace that will be updated

    Returns:
        Password if found, None otherwise
    """
    import database

    try:
        db_manager = database.DBManager(database.Table(db_filename))
        res = db_manager.get_password(login)
        if res:
            opt.login = res[0]
            return res[1]
        return None
    except Exception as e:
        print(e)
        return None


def check_image_filename(
    option: str, opt_str: str, value: str, parser: argparse.ArgumentParser
) -> None:
    """Check image format for graph saving.

    Args:
        option: Option name
        opt_str: Option string
        value: Image filename
        parser: Argument parser instance

    Raises:
        argparse.ArgumentTypeError: If format is invalid
    """
    if not value:
        raise argparse.ArgumentTypeError("option -s: Can't use without parameter")
    if not parser.values.graph:
        raise argparse.ArgumentTypeError("option -s: Can't use without -g")
    if any(value.endswith(ext) for ext in __FIGURE_FORMATS__):
        parser.values.imagefilename = value
    else:
        raise argparse.ArgumentTypeError(
            f"option -s: Not correct file format. Use formats: {__FIGURE_FORMATS__}"
        )


class UI:
    """User interface for displaying ByFly information."""

    def __init__(self, byfly_user: byflyuser.ByFlyUser) -> None:
        self._byfly_user = byfly_user

    def print_additional_info(self) -> bool:
        """Print additional statistics information."""
        total_stat_info = self._byfly_user.get_additional_info()
        if total_stat_info:
            s = (
                f"Суммарный трафик - {total_stat_info.total_traf} {self._byfly_user.get_traf_measure()}\n"
                f"Превышение стоимости - {total_stat_info.total_cost} {self._byfly_user.get_money_measure()}"
            )
            self.print_to_console(s)
            return True
        return False

    def print_to_console(self, s: str, end: str = "\n") -> None:
        """Print string to console.

        Args:
            s: String to print
            end: String to append after print
        """
        print(s, end=end)

    def print_info(self, only_balance: bool = False) -> bool:
        """Get and print account information.

        Args:
            only_balance: If True, only print balance

        Returns:
            True if successful, False otherwise
        """
        info = self._byfly_user.get_account_info_page()
        if not info:
            return False
        if only_balance:
            self.print_to_console(f"{info.balance}", end="")
            return True
        traf = ""
        duration = ""
        self.print_to_console(
            f"Абонент - {info.full_name}\n"
            f"Тариф   - {info.plan}\n"
            f"Баланс  - {info.balance} {self._byfly_user.get_money_measure()} {traf} {duration}"
        )
        return True

    def print_claim_payments_status(self) -> None:
        """Print active claim payment information."""
        payments = self._byfly_user.get_payments_page()
        for payment in payments:
            if payment.is_active:
                self.print_to_console(
                    f"Обещанный платеж от {payment.date} на сумму {payment.cost} "
                    f"{self._byfly_user.get_money_measure()}"
                )
                break


class Program:
    """Main program class for ByFly balance checker."""

    def ui(self, opt: argparse.Namespace, showgraph: Optional[str] = None) -> Optional[int]:
        """Output all information.

        Args:
            opt: Command-line options
            showgraph: If 'always', graph is shown and saved to file

        Returns:
            Exit code (0, 1, or 2)
        """
        if opt.graph:
            import_plot()

        user = byflyuser.ByFlyUser(opt.login, opt.password)
        ui = UI(user)

        try:
            user.login()
        except byflyuser.ByflyException as e:
            print(byflyuser.get_exception_str(e))
            return 2

        if opt.quiet:
            ui.print_info(True)
            return 0

        ui.print_info()
        ui.print_additional_info()
        ui.print_claim_payments_status()

        if opt.graph and HAS_MATPLOT:
            plt = plotinfo.Plotter()
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
                    user.get_log(previous_period=opt.previous_period),
                    title=user.info,
                    show=show,
                    fname=fname,
                )
            elif opt.graph == "traf":
                plt.plot_traf_allocation(
                    user.get_log(previous_period=opt.previous_period),
                    title=user.info,
                    show=show,
                    fname=fname,
                )

        return 0

    def setup_cmd_parser(self) -> argparse.ArgumentParser:
        """Set up command-line argument parser.

        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(description="Проверка баланса ByFly", prog="ByFlyPy")
        parser.add_argument(
            "-i",
            action="store_true",
            dest="interactive",
            help="enable interactive mode",
        )
        parser.add_argument("-l", "--login", action="store", type=str, dest="login", help="login")
        parser.add_argument(
            "--list",
            type=str,
            dest="check_list",
            metavar="<filename>",
            help="check accounts in file. Each line of file must be login:password",
        )
        parser.add_argument("-p", "--p", action="store", type=str, dest="password", help="password")
        parser.add_argument(
            "-g",
            "--graph",
            action="store",
            dest="graph",
            type=str,
            choices=["traf", "time"],
            help="plot a graph. Parameters MUST BE traf or time",
        )
        parser.add_argument(
            "--previous",
            action="store_true",
            dest="previous_period",
            help="get statistic for previous month",
            default=False,
        )
        parser.add_argument(
            "-s",
            "--save",
            action="store",
            type=str,
            dest="imagefilename",
            help="save graph to file",
        )
        parser.add_argument(
            "-n",
            "--nologo",
            action="store_true",
            dest="nologo",
            help="don't show logo at startup",
        )
        parser.add_argument(
            "--pause",
            action="store_true",
            dest="pause",
            default=False,
            help="don't close console window immediately",
        )
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            help="enable debug",
            default=False,
        )
        parser.add_argument("--db", action="store", type=str, dest="db", help="database filename")
        parser.add_argument(
            "-q",
            action="store_true",
            dest="quiet",
            help="print balance and exit",
            default=False,
        )
        parser.set_defaults(
            interactive=False,
            graph=None,
            imagefilename=None,
            nologo=False,
            debug=False,
        )
        return parser

    def interactive_mode_handler(self, opt: argparse.Namespace, database_filename: str) -> None:
        """Handle interactive mode.

        Args:
            opt: Command-line options
            database_filename: Path to database file
        """
        try:
            while True:
                a = input("Login:")
                if a == "":
                    print("Incorrect data")
                    sys.exit(1)
                opt.login = a
                a = pass_from_db(opt.login, database_filename, opt)
                if a is None:
                    a = getpass.getpass("Password:")
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
        """Handle list checker mode.

        Args:
            opt: Command-line options
        """
        import os.path

        try:
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
    ) -> Optional[int]:
        """Handle non-interactive mode.

        Args:
            opt: Command-line options
            database_filename: Path to database file

        Returns:
            Exit code from ui method
        """
        if not opt.login:
            sys.exit()
        if not opt.password:
            opt.password = pass_from_db(opt.login, database_filename, opt)
            if not opt.password:
                print("Login not found")
                sys.exit(1)
        return self.ui(opt)

    def main(self) -> None:
        """Main entry point for the program."""
        parser = self.setup_cmd_parser()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit()

        opt = parser.parse_args()

        byflyuser._DEBUG_ = opt.debug
        log_level = logging.DEBUG if opt.debug else logging.CRITICAL
        logging.basicConfig(stream=sys.stdout, level=log_level)

        if opt.pause:
            atexit.register(pause)

        if not opt.nologo and not opt.quiet:
            parser.print_version()

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
