#!/usr/bin/python

# Copyright: (c) 2025, Michael Kearey (adapted from NS1 community)
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
---
module: ns1_notifier_list_info

short_description: List all NS1 notification lists and their IDs.

version_added: "2.10"

description:
  - Retrieves a list of all notification lists configured in NS1 Connect, 
    allowing other tasks to look up list IDs by name for monitor job configuration.

options:
  apiKey:
    description:
      - Unique client api key.
    type: str
    required: true
'''

EXAMPLES = '''
- name: Fetch All Notification Lists Globally
  ns1_notifier_list_info:
    apiKey: "{{ ns1_token }}"
  register: all_notifiers_result

- name: Debug Notifier List ID by Name
  debug:
    msg: "ID for MKeareyOnly is {{ all_notifiers_result.notifiers | selectattr('name', 'equalto', 'MKeareyOnly') | map(attribute='id') | first }}"

'''

RETURN = '''
notifiers:
    description: A dictionary containing the full list of notification lists.
    type: list
    returned: always
    sample:
        - id: 68e867b77994c100013efd80
          name: MKeareyOnly
          notify_list: [{...}]
'''

import copy # noqa

try:
    from ansible.module_utils.ns1 import NS1ModuleBase
except ImportError:
    from module_utils.ns1 import NS1ModuleBase  # noqa

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    pass


class NS1NotifierListInfo(NS1ModuleBase):
    def __init__(self):
        # Only apiKey is required, bypassing strict argument checks for lookup tasks
        self.module_arg_spec = dict(
            apiKey=dict(required=True, type='str'),
        )
        NS1ModuleBase.__init__(self, self.module_arg_spec, supports_check_mode=True)

    def get_list(self):
        """Fetches the complete list of notification lists from the API."""
        try:
            # ns1.notifylists().list() returns the raw list of dictionaries
            lists = self.ns1.notifylists().list()
            
            # Convert list to dictionary keyed by 'name' for easier Ansible lookup
            return lists
            
        except ResourceException as re:
            self.module.fail_json(msg="Error retrieving notification lists: %s" % re.message)

    def exec_module(self):
        """Entry point for the module."""
        
        # The module is always run as read-only, so changed=False is the default.
        
        notifiers = self.get_list()
        
        self.module.exit_json(changed=False, notifiers=notifiers)


def main():
    list_info_module = NS1NotifierListInfo()
    list_info_module.exec_module()


if __name__ == '__main__':
    main()
