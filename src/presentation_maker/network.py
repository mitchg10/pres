"""Helpers for serving a preview on the local network (phone/tablet access)."""

from __future__ import annotations

import socket

# Quarto's own preview default; also the port we suggest first for --network.
DEFAULT_PORT = 4200

# How many ports above the requested one to try before giving up.
PORT_SCAN_RANGE = 20

# ANSI backgrounds for QR modules. Explicit colors (rather than the terminal's
# own fg/bg) keep the code scannable in a dark-theme terminal, where an inverted
# QR is rejected by many phone cameras.
_QR_DARK = "\033[40m  \033[0m"
_QR_LIGHT = "\033[107m  \033[0m"


def get_lan_ip() -> str | None:
    """Return this machine's LAN IP address, or None if it can't be determined.

    Connecting a UDP socket sends no packets — it just asks the OS to pick the
    interface it would use to reach the internet, which is the one a phone on
    the same WiFi can also reach. This is portable, unlike parsing `ipconfig`.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def _is_port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False


def find_free_port(preferred: int = DEFAULT_PORT) -> int:
    """Return the first free port at or above `preferred`.

    We have to commit to a port before launching quarto so the URL and QR code
    can be printed up front, which means checking availability ourselves rather
    than letting quarto pick.
    """
    for port in range(preferred, preferred + PORT_SCAN_RANGE):
        if _is_port_free(port):
            return port
    raise RuntimeError(
        f"No free port found between {preferred} and {preferred + PORT_SCAN_RANGE - 1}. "
        "Stop any other previews, or pass a different --port."
    )


def render_qr(url: str) -> str | None:
    """Render `url` as a scannable QR code made of ANSI-colored blocks.

    Returns None if the optional `qrcode` package isn't installed, so a missing
    dependency degrades to a plain URL instead of breaking the preview.
    """
    try:
        import qrcode
    except ImportError:
        return None

    try:
        code = qrcode.QRCode(border=4)
        code.add_data(url)
        code.make(fit=True)
        matrix = code.get_matrix()
    except Exception as error:  # noqa: BLE001 - a QR failure must not stop the preview
        raise RuntimeError(f"Could not render a QR code for {url}: {error}") from error

    return "\n".join(
        "".join(_QR_DARK if module else _QR_LIGHT for module in row) for row in matrix
    )
