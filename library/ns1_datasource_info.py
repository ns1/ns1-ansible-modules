#!/usr/bin/python

# Copyright: (c) 2020, NS1
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
module: ns1_datasource_info

short_description: List available datasources and their feeds.

version_added: "2.9"

description:
  - List available datasources and their feeds. Use this to reference feeds
    in e.g. ns1_record answer meta.

options:
  apiKey:
    description:
      - Unique client api key that can be created via the NS1 portal.
    type: str
    required: true
  endpoint:
    description:
      - NS1 API endpoint. Defaults to https://api.nsone.net/v1/
    type: str
    required: false
  ignore_ssl:
    description:
      - Whether to ignore SSL errors. Defaults to false
    type: bool
    required: false
'''

EXAMPLES = '''
- name: Register the list of datasources
  ns1_datasource_info
    apiKey: "{{ ns1_token }}"
  register: datasource_info
- name: Reference a datafeed by ID, with a variable
  debug:
    var: datasource_info.datasources.datadog.feeds[0].id

'''

try:
    from ansible.module_utils.ns1 import NS1ModuleBase
except ImportError:
    # import via absolute path when running via pytest
    from module_utils.ns1 import NS1ModuleBase  # noqa

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    # This is handled in NS1 module_utils
    pass


class NS1DataSources(NS1ModuleBase):
    def __init__(self):
        self.module_arg_spec = dict()
        NS1ModuleBase.__init__(
            self, self.module_arg_spec, supports_check_mode=True
        )

    def get_datasources(self):
        to_return = {}
        try:
            raw_response = self.ns1.datasource().list()
        except ResourceException as re:
            self.module.fail_json(
                msg="error code %s - %s " % (re.response.code, re.message)
            )
        else:
            to_return = {x["name"]: x for x in raw_response}

        return to_return

    def exec_module(self):
        datasources = self.get_datasources()
        self.module.exit_json(datasources=datasources)


def main():
    ds = NS1DataSources()
    result = ds.exec_module()
    ds.module.exit_json(**result)


if __name__ == '__main__':
    main()
