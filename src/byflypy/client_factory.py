"""Client factory: creates and authenticates ByFly clients from CLI options."""

from __future__ import annotations

import argparse

from byflypy.clients.api_client import ByFlyApiClient, TokenManager
from byflypy.clients.html_client import ByFlyHtmlClient, get_exception_str
from byflypy.console import Console
from byflypy.database import DBManager, Table
from byflypy.exceptions import ByFly2FARequiredError, ByFlyError


def create_client(
    opt: argparse.Namespace,
    database_filename: str,
    console: Console,
) -> tuple[ByFlyApiClient | ByFlyHtmlClient | None, int | None]:
    """Create and authenticate a client from parsed options.

    Returns:
        (client, None) on success, (None, exit_code) on error.
    """
    if opt.use_api_v1:
        return _create_html_client(opt, database_filename, console)
    return _create_api_client(opt, console)


def _create_html_client(
    opt: argparse.Namespace,
    database_filename: str,
    console: Console,
) -> tuple[ByFlyHtmlClient | None, int | None]:
    """Create and login HTML (API v1) client."""
    if not opt.login:
        return (None, None)
    if not opt.password:
        _load_password_from_db(opt, database_filename, console)
        opt.password = opt.password or console.get_password("Password:")
    client = ByFlyHtmlClient(
        opt.login,
        opt.password or "",
        debug=getattr(opt, "debug", False),
    )
    try:
        client.login()
    except ByFlyError as e:
        console.print(get_exception_str(e))
        return (None, 2)
    return (client, None)


def _load_password_from_db(
    opt: argparse.Namespace,
    database_filename: str,
    console: Console,
) -> None:
    """Load password from database into opt.login/opt.password."""
    try:
        db_manager = DBManager(Table(database_filename))
        res = db_manager.get_password(opt.login)
        if res:
            opt.login = res[0]
            opt.password = res[1]
    except Exception as e:
        console.print(str(e))


def _create_api_client(
    opt: argparse.Namespace,
    console: Console,
) -> tuple[ByFlyApiClient | None, int | None]:
    """Create and login REST API v2 client; resolve btk_id if needed."""
    phone = opt.account_phone
    if phone and not phone.startswith("+"):
        phone = "+" + phone

    client = None
    if opt.access_token:
        client = ByFlyApiClient(
            phone=opt.account_phone,
            password=None,
            sms_code=None,
            login=opt.login,
        )
        client.set_access_token(opt.access_token)
    elif phone:
        token_manager = TokenManager(console=console)
        if not token_manager.load(phone) and not opt.password:
            opt.password = console.get_password("Password:")
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
            code = console.input("Enter SMS code from phone: ")
            if not code:
                return (None, 2)
            client.set_sms_code(code)
            try:
                client.login()
            except ByFly2FARequiredError:
                console.print("Invalid or expired SMS code")
                return (None, 2)
        except ByFlyError as e:
            console.print(get_exception_str(e))
            return (None, 2)
        console.print(f"Access token: {client.access_token}")
    else:
        console.print("Error: --account-phone or --access-token is required for API v2")
        return (None, 2)

    if client is None:
        return (None, 2)

    # Resolve btk_id (contract selection)
    if opt.login:
        contracts = client.get_contracts()
        btk_ids = []
        for contract in contracts:
            btk_ids.append(contract.btk_id)
            if contract.btk_id == opt.login:
                client._login = contract.login
        if not client._login:
            console.print(f"Error: Btk ID '{opt.login}' not found for this account")
            console.print(f"Available Btk IDs: {', '.join(btk_ids)}")
            return (None, 2)

    if not opt.login:
        contracts = client.get_contracts()
        filled_contracts = [c for c in contracts if c.btk_id]
        if len(filled_contracts) == 0:
            console.print("Error: No internet logins found for this account")
            return (None, 2)
        if len(filled_contracts) == 1:
            contract = filled_contracts[0]
            opt.login = contract.btk_id
            client._login = contract.login
        else:
            console.print("Available internet logins (Btk ID):")
            for contract in filled_contracts:
                tariff = None
                if contract.applications and contract.applications[0].tariff:
                    tariff = contract.applications[0].tariff.name
                console.print(
                    f"  - {contract.btk_id}: {contract.name} (tariff: {tariff}) (balance: {contract.balance})"
                )
            console.print("\nPlease specify one with --login")
            return (None, 2)

    return (client, None)
