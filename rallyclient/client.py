# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import oslo.i18n

from rallyclient.openstack.common import importutils

oslo.i18n.install('rallyclient')


def get_client(api_version, **kwargs):
    """Get versioned client.

    :param api_version: the API version to use. Valid value: '1'.
    :param kwargs: keyword args containing credentials, either:
            * rally_url: rally API endpoint
    """

    endpoint = kwargs.get('rally_url')

    cli_kwargs = {
        'timeout': kwargs.get('timeout')
    }

    return Client(api_version, endpoint, **cli_kwargs)


def Client(version, *args, **kwargs):
    module = importutils.import_versioned_module(version, 'client')
    client_class = getattr(module, 'Client')
    return client_class(*args, **kwargs)
