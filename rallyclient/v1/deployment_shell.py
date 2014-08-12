# Copyright 2014 Mirantis, Inc.
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

import json
import yaml
import os
import pprint

from rallyclient.openstack.common import cliutils


def print_deployments(self, deployment_list=None):
    """Print list of deployments."""
    headers = ['UUID', 'Created at', 'Name', 'Status', 'Active']

    table_rows = []
    if deployment_list:
        cliutils.print_list(table_rows, headers,
                            sortby_index=headers.index('created_at'))
    else:
        print(_("There are no deployments. "
                "To create a new deployment, use:"
                "\nrally deployment create"))


@cliutils.arg(
    '--name',
    type=str, required=True, help='A name of the deployment.')
@cliutils.arg(
    '--fromenv',
    action='store_true',
    help='Read environment variables instead of config file')
@cliutils.arg(
    '--filename',
    type=str, required=False,
    help='A path to the configuration file of the deployment.')
@cliutils.arg(
    '--no-use',
    action='store_false', dest='do_use',
    help="Don't set new deployment as default for future operations")
def do_create(cc, name, fromenv=False, filename=None, do_use=False):
    """Create a new deployment on the basis of configuration file.

    :param fromenv: boolean, read environment instead of config file
    :param filename: a path to the configuration file
    :param name: a name of the deployment
    """

    if fromenv:
        required_env_vars = ["OS_USERNAME", "OS_PASSWORD", "OS_AUTH_URL",
                             "OS_TENANT_NAME"]

        unavailable_vars = [v for v in required_env_vars
                            if v not in os.environ]
        if unavailable_vars:
            print("The following environment variables are required but "
                  "not set: %s" % ' '.join(unavailable_vars))
            return 1

        config = {
            "type": "ExistingCloud",
            "endpoint": {
                "auth_url": os.environ['OS_AUTH_URL'],
                "username": os.environ['OS_USERNAME'],
                "password": os.environ['OS_PASSWORD'],
                "tenant_name": os.environ['OS_TENANT_NAME']
            }
        }
        region_name = os.environ.get('OS_REGION_NAME')
        if region_name and region_name != 'None':
            config['endpoint']['region_name'] = region_name
    else:
        if not filename:
            print("Either --filename or --fromenv is required")
            return 1
        with open(filename, 'rb') as deploy_file:
            config = yaml.safe_load(deploy_file.read())

    deployment = cc.deployments.create(config, name)
    print_deployments(deployment_list=[deployment])
    if do_use:
        cc.deployments.use(deployment['uuid'])


@cliutils.arg(
    '--uuid',
    dest='deploy_id', type=str, required=False, help='UUID of a deployment.')
def do_recreate(cc, deploy_id):
    """Destroy and create an existing deployment.

    :param deploy_id: a UUID of the deployment
    """
    cc.deployments.recreate(deploy_id)

@cliutils.arg(
    '--uuid',
    dest='deploy_id', type=str, required=False, help='UUID of a deployment.')
def do_destroy(cc, deploy_id):
    """Destroy the deployment.

    Release resources that are allocated for the deployment. The
    Deployment, related tasks and their results are also deleted.

    :param deploy_id: a UUID of the deployment
    """
    cc.deployments.destroy(deploy_id)


def do_list(cc):
    """Print list of deployments."""
    print_deployments(cc, cc.deployments.list())


@cliutils.arg(
    '--uuid',
    dest='deploy_id', type=str, required=False, help='UUID of a deployment.')
@cliutils.arg(
    '--json',
    dest='output_json', action='store_true',
    help='Output in json format(default)')
@cliutils.arg(
    '--pprint',
    dest='output_pprint', action='store_true',
    help='Output in pretty print format')
def do_config(cc, deploy_id, output_json=None, output_pprint=None):
    """Print on stdout a config of the deployment.

        Output can JSON or Pretty print format.

    :param deploy_id: a UUID of the deployment
    :param output_json: Output in json format (Default)
    :param output_pprint: Output in pretty print format
    """
    deploy = cc.deployments.get(deploy_id)
    result = deploy['config']
    if all([output_json, output_pprint]):
        print(_('Please select only one output format'))
        return 1
    elif output_pprint:
        print()
        pprint.pprint(result)
        print()
    else:
        print(json.dumps(result))


@cliutils.arg(
    '--uuid',
    dest='deploy_id', type=str, required=False, help='UUID of a deployment.')
def do_endpoint(cc, deploy_id):
    """Print endpoint of the deployment.

    :param deploy_id: a UUID of the deployment
    """
    headers = ['auth_url', 'username', 'password', 'tenant_name',
               'region_name', 'use_public_urls', 'admin_port']
    endpoints = cc.deployments.get(deploy_id)['endpoints']
    cliutils.print_list(endpoints, headers)


@cliutils.arg(
    '--uuid',
    dest='deploy_id', type=str, required=False, help='UUID of a deployment.')
def check(cc, deploy_id=None):
    """Check the deployment.

    Check keystone authentication and list all available services.

    :param deploy_id: a UUID of the deployment
    """
    headers = ['services', 'type', 'status']
    services = cc.deployments.get(deploy_id)['services']
    cliutils.print_list(services, headers)
