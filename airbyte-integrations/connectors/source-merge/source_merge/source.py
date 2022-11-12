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

from MergePythonSDK.crm.api.opportunities_api import OpportunitiesApi
from MergePythonSDK.crm.api.users_api import UsersApi
from MergePythonSDK.crm.api.accounts_api import AccountsApi
from MergePythonSDK.shared import Configuration, ApiClient

# Basic full refresh stream
class MergeStream(HttpStream, ABC):
    """
    TODO remove this comment

    This class represents a stream output by the connector.
    This is an abstract base class meant to contain all the common functionality at the API level e.g: the API base URL, pagination strategy,
    parsing responses etc..

    Each stream should extend this class (or another abstract subclass of it) to specify behavior unique to that stream.

    Typically for REST APIs each stream corresponds to a resource in the API. For example if the API
    contains the endpoints
        - GET v1/customers
        - GET v1/employees

    then you should have three classes:
    `class MergeStream(HttpStream, ABC)` which is the current class
    `class Customers(MergeStream)` contains behavior to pull data for customers using v1/customers
    `class Employees(MergeStream)` contains behavior to pull data for employees using v1/employees

    If some streams implement incremental sync, it is typical to create another class
    `class IncrementalMergeStream((MergeStream), ABC)` then have concrete stream implementations extend it. An example
    is provided below.

    See the reference docs for the full list of configurable options.
    """

    # TODO: Fill in the url base. Required.
    url_base = "https://api.merge.dev/api/crm/v1/"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        TODO: Override this method to define a pagination strategy. If you will not be using pagination, no action is required - just return None.

        This method should return a Mapping (e.g: dict) containing whatever information required to make paginated requests. This dict is passed
        to most other methods in this class to help you form headers, request bodies, query params, etc..

        For example, if the API accepts a 'page' parameter to determine which page of the result to return, and a response from the API contains a
        'page' number, then this method should probably return a dict {'page': response.json()['page'] + 1} to increment the page count by 1.
        The request_params method should then read the input next_page_token and set the 'page' param to next_page_token['page'].

        :param response: the most recent response from the API
        :return If there is another page in the result, a mapping (e.g: dict) containing information needed to query the next page in the response.
                If there are no more pages in the result, return None.
        """
        cursor = response.json()['next']
        if cursor is not None:
            return {'cursor': cursor}
        else:
            return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        TODO: Override this method to define any query parameters to be set. Remove this method if you don't need to define request params.
        Usually contains common params e.g. pagination size etc.
        """
        if next_page_token is not None:
            return {'cursor': next_page_token['cursor']}
        else:
            return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        return response.json()['results']

class Users(MergeStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """
    # TODO: Fill in the primary key. Required. This is usually a unique field in the stream, like an ID or a timestamp.
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "users"

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
    """
    Auth class for Personal Access Token
    https://help.getharvest.com/api-v2/authentication-api/authentication/authentication/#personal-access-tokens
    """

# Source
class SourceMerge(AbstractSource):
    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, any]:
        try:
            headers = {"Authorization": f"Bearer {config['access_key']}", "X-Account-Token": config['account_token']}
            params = {}

            resp = requests.get(f"{MergeStream.url_base}users", params=params, headers=headers)
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
        return [Users(authenticator=auth)]
