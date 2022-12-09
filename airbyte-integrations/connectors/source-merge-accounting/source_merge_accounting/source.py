#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator

class MergeStream(HttpStream, ABC):
    url_base = "https://api.merge.dev/api/accounting/v1/"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        cursor = response.json()['next']
        if cursor is not None:
            return {'cursor': cursor}
        else:
            return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        if next_page_token is not None:
            return {'cursor': next_page_token['cursor']}
        else:
            return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()['results']

class Contacts(MergeStream):
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "contacts"

class Invoices(MergeStream):
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "invoices"

class Items(MergeStream):
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "items"

class Transactions(MergeStream):
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "transactions"

class Accounts(MergeStream):
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "accounts"

class MergeAuthMixin:
    """
    Mixin class for providing additional HTTP header for specifying account ID
    https://help.getharvest.com/api-v2/authentication-api/authentication/authentication/
    """

    def __init__(self, *, account_token: str, **kwargs):
        super().__init__(**kwargs)
        self.account_token = account_token

    def get_auth_header(self) -> Mapping[str, Any]:
        return {**super().get_auth_header(), "X-Account-Token": self.account_token}


class MergeAuthenticator(MergeAuthMixin, TokenAuthenticator):
    pass

# Source
class SourceMergeAccounting(AbstractSource):
    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, any]:
        try:
            headers = {"Authorization": f"Bearer {config['access_key']}", "X-Account-Token": config['account_token']}
            params = {}

            resp = requests.get(f"{MergeStream.url_base}items", params=params, headers=headers)
            status = resp.status_code
            logger.info(f"Ping response code: {status}")
            if status == 200:
                return True, None
            # When API requests is sent but the requested data is not available or the API call fails
            # for some reason, a JSON error is returned.
            # https://exchangeratesapi.io/documentation/#errors
            return False, resp.json().get('detail')
        except Exception as e:
            return False, e

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        auth = MergeAuthenticator(token=config['access_key'], account_token=config['account_token'])
        return [
            Contacts(authenticator=auth), 
            Invoices(authenticator=auth), 
            Items(authenticator=auth), 
            Transactions(authenticator=auth),
            Accounts(authenticator=auth),
        ]
