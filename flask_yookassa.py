from __future__ import annotations
from collections.abc import Iterable
from functools import wraps
from ipaddress import (
    ip_address,
    ip_network,
    IPv4Address,
    IPv6Address,
    IPv4Network,
    IPv6Network,
)
import typing as t

from flask import (
    __version__ as FLASK_VERSION,
    abort,
    current_app,
    request,
    Flask,
)
from flask.typing import ResponseReturnValue
from yookassa import Configuration, Deal, Payment, Refund
from yookassa.domain.common.user_agent import Version
from yookassa.domain.exceptions import ApiError
from yookassa.domain.notification import WebhookNotificationFactory
from werkzeug.exceptions import HTTPException


__all__ = ('Yookassa',)


ErrorHandlerCallback = t.Callable[
    [t.Dict[str, t.Any], int],
    ResponseReturnValue
]
IPOrMask = t.Union[
    IPv4Address, IPv6Address, IPv4Network, IPv6Network
]
WhileListAllowedArg = t.Union[str, t.Iterable[str]]
V = t.TypeVar('V', bound=t.Callable[..., ResponseReturnValue])

RESOURCE_MAP = {
    'deal': Deal,
    'payment': Payment,
    'refund': Refund,
}


class WhileList:
    __slots__ = ('_allowed',)

    def __init__(self, allowed: t.Iterable[str]) -> None:
        self._allowed: t.Set[IPOrMask] = set()
        self.__iadd__(allowed)

    def _cast(self, ip: str) -> IPOrMask:
        if ip.find('/') == -1:
            return ip_address(ip)
        else:
            return ip_network(ip)

    def _cast_argument(self, allowed: WhileListAllowedArg) -> t.Set[IPOrMask]:
        if isinstance(allowed, str):
            return {self._cast(allowed)}
        elif isinstance(allowed, Iterable):
            return {self._cast(i) for i in allowed}
        else:
            raise TypeError

    def __iadd__(self, allowed: WhileListAllowedArg) -> WhileList:
        try:
            self._allowed.update(self._cast_argument(allowed))
            return self
        except TypeError:
            return NotImplemented

    def __isub__(self, allowed: WhileListAllowedArg) -> WhileList:
        try:
            self._allowed.difference_update(
                self._cast_argument(allowed)
            )
            return self
        except TypeError:
            return NotImplemented

    def __contains__(self, address: str) -> bool:
        ip = ip_address(address)

        for i in self._allowed:
            if isinstance(i, (IPv4Address, IPv6Address)):
                found = i == ip
            else:
                found = ip in i

            if found:
                return True

        return False


class Yookassa:
    __slots__ = (
        '_allowed_ip',
        '_handle_error_callback',
        'Deal',
        'Payment',
        'Refund',
    )

    def __init__(self, app: t.Optional[Flask] = None) -> None:
        self._allowed_ip = WhileList({
            '185.71.76.0/27',
            '185.71.77.0/27',
            '77.75.153.0/25',
            '77.75.156.11',
            '77.75.156.35',
            '77.75.154.128/25',
            '2a02:5180::/32',
        })
        self._handle_error_callback: t.Optional[ErrorHandlerCallback] = None
        self.Deal = Deal
        self.Payment = Payment
        self.Refund = Refund

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config.setdefault('YOOKASSA_SHOP_ID', None)
        app.config.setdefault('YOOKASSA_SHOP_SECRET_KEY', None)
        app.config.setdefault('YOOKASSA_NOTIFICATIONS_IP', set())

        Configuration.configure(
            account_id=app.config['YOOKASSA_SHOP_ID'],
            secret_key=app.config['YOOKASSA_SHOP_SECRET_KEY'],
        )
        Configuration.configure_user_agent(
            framework=Version('Flask', FLASK_VERSION),
        )

        self._allowed_ip += app.config['YOOKASSA_NOTIFICATIONS_IP']

        app.register_error_handler(ApiError, self.handle_api_error)

    def errorhandler(self, func: V) -> V:
        self._handle_error_callback = func
        return func

    def handle_api_error(self, err: ApiError) -> ResponseReturnValue:
        code = err.HTTP_CODE if hasattr(err, 'HTTP_CODE') else 400
        resp = err.args[0]

        if self._handle_error_callback is None:
            return resp, code

        try:
            return self._handle_error_callback(resp, code)
        except HTTPException as err:
            return current_app.handle_http_exception(err)

    def hookhandler(self, func: V) -> V:
        @wraps(func)
        def wrapper(*args: t.Any, **kwargs: t.Any) -> ResponseReturnValue:
            if t.cast(str, request.remote_addr) not in self._allowed_ip:
                current_app.logger.error('The request was rejected as an unknown IP address.')
                abort(403)

            try:
                notification = WebhookNotificationFactory().create(request.json)
            except Exception as err:
                current_app.logger.error(str(err))
                abort(400)

            name, _ = notification.event.split('.', 1)
            resource_class = RESOURCE_MAP[name]
            obj = notification.object
            found = resource_class.find_one(obj.id)

            if obj.status != found.status:
                current_app.logger.error('The resource has a different status.')
                abort(403)

            return func(notification, *args, **kwargs)
        return t.cast(V, wrapper)
