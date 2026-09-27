"""Announcing the server on the local network (mDNS / DNS-SD).

The Android app's "Found on this network" list: the server registers a
``_downtify._tcp`` service with a TXT record the app reads before it
connects - server id, name, version, API version, port and scheme - so a
phone on the same network finds it without anyone typing an address.

Uses ``python-zeroconf`` (pure Python, plus its one small dependency,
``ifaddr``): mDNS has to answer multicast queries for as long as the
server runs, which is not something to hand-roll, and the alternative -
Avahi over D-Bus - isn't there in the Alpine image or on Windows/macOS.

Multicast only reaches the LAN when the server is on it: in Docker's
default bridge network the announcement stays inside the container
network. ``network_mode: host`` fixes that; otherwise the app's manual
address entry still works. ``DOWNTIFY_DISCOVERY=false`` turns the
announcement off.
"""

from __future__ import annotations

import os
import socket
from typing import Any, Optional

import ifaddr
from loguru import logger
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from .server_identity import API_VERSION, ServerIdentity

SERVICE_TYPE = '_downtify._tcp.local.'

_VIRTUAL_PREFIXES = ('docker', 'br-', 'veth', 'virbr', 'cni', 'flannel')


def discovery_enabled() -> bool:
    raw = os.getenv('DOWNTIFY_DISCOVERY', '').strip().lower()
    return raw not in {'0', 'false', 'no', 'off'}


def instance_name(name: str) -> str:
    """A DNS-SD instance label for *name*: no dots, at most 63 bytes."""

    text = ' '.join(str(name or 'Downtify').replace('.', ' ').split())
    encoded = text.encode()[:63]
    return encoded.decode(errors='ignore').strip() or 'Downtify'


def txt_record(
    identity: ServerIdentity, *, version: str, port: int, scheme: str
) -> dict[str, str]:
    """What the app reads before connecting."""

    return {
        'id': identity.server_id,
        'name': identity.name,
        'version': version,
        'api': str(API_VERSION),
        'port': str(port),
        'scheme': scheme,
        'path': '/',
    }


def local_addresses(host: str = '') -> list[str]:
    """The addresses to announce: the one the server is bound to, or -
    bound to all (``0.0.0.0``/``::``) - every non-loopback IPv4 address
    of the machine."""

    if host and host not in {'0.0.0.0', '::', ''}:
        return [host]
    found = []
    for adapter in ifaddr.get_adapters():
        # Container and VM bridges aren't where the phones are.
        if str(adapter.nice_name).startswith(_VIRTUAL_PREFIXES):
            continue
        for ip in adapter.ips:
            if (
                isinstance(ip.ip, str)
                and not ip.ip.startswith('127.')
                and not ip.ip.startswith('169.254.')
            ):
                found.append(ip.ip)
    return sorted(set(found))


class Announcer:
    """Registers (and keeps up to date) this server's mDNS service."""

    def __init__(
        self,
        identity: ServerIdentity,
        *,
        version: str,
        port: int,
        host: str = '',
        scheme: str = 'http',
    ) -> None:
        self._identity = identity
        self._version = version
        self._port = port
        self._host = host
        self._scheme = scheme
        self._zc: Any = None
        self._info: Any = None

    def _service_info(self) -> Any:
        addresses = local_addresses(self._host)
        return ServiceInfo(
            SERVICE_TYPE,
            f'{instance_name(self._identity.name)}.{SERVICE_TYPE}',
            addresses=[socket.inet_aton(a) for a in addresses if '.' in a],
            port=self._port,
            properties=txt_record(
                self._identity,
                version=self._version,
                port=self._port,
                scheme=self._scheme,
            ),
            server=f'downtify-{self._identity.server_id[:8]}.local.',
        )

    async def start(self) -> bool:
        try:
            self._info = self._service_info()
            self._zc = AsyncZeroconf()
            await self._zc.async_register_service(
                self._info, allow_name_change=True
            )
        except Exception:
            logger.opt(exception=True).warning(
                'LAN discovery: could not announce the server'
            )
            await self.stop()
            return False
        logger.info(
            'LAN discovery: announced "{}" on port {} ({})',
            self._identity.name,
            self._port,
            ', '.join(local_addresses(self._host)) or 'no addresses',
        )
        return True

    async def update(self, _name: Optional[str] = None) -> None:
        """Announce again after the server was renamed."""

        if self._zc is None or self._info is None:
            return
        try:
            await self._zc.async_unregister_service(self._info)
            self._info = self._service_info()
            await self._zc.async_register_service(
                self._info, allow_name_change=True
            )
        except Exception:
            logger.opt(exception=True).warning(
                'LAN discovery: could not update the announcement'
            )

    async def stop(self) -> None:
        if self._zc is None:
            return
        try:
            if self._info is not None:
                await self._zc.async_unregister_service(self._info)
            await self._zc.async_close()
        except Exception:
            logger.opt(exception=True).debug('LAN discovery: stop failed')
        self._zc = None
        self._info = None
