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
module: ns1_notifier_list

short_description: Create, modify, and delete NS1 notification lists.

version_added: "2.10"

description:
  - Manages notification lists (recipient groups) used by monitor jobs to send alerts.

options:
  apiKey:
    description:
      - Unique client api key.
    type: str
    required: true
  state:
    description:
      - Whether the notification list should be C(present) or C(absent).
    type: str
    default: present
    choices:
      - absent
      - present
  name:
    description:
      - The human-readable name for the notification list (e.g., 'MKeareyOnly').
    type: str
    required: true
  notify_list:
    description:
      - Array of notification targets (recipients/channels) for this list.
    type: list
    required: true
    suboptions:
      type:
        description:
          - The type of notification channel (e.g., 'email', 'datafeed', 'pagerduty').
        type: str
        required: true
      config:
        description:
          - Dictionary containing type-specific configuration (e.g., 'email' address or 'sourceid').
        type: dict
        required: true
'''

EXAMPLES = '''
- name: Ensure specific notification list is present
  ns1_notifier_list:
    apiKey: "{{ ns1_token }}"
    name: MyDevOpsTeam
    state: present
    notify_list:
      - type: email
        config:
          email: support@example.com
      - type: datafeed
        config:
          sourceid: 3f841cfa37e393be05252371af551457 # Data source ID
'''

RETURN = '''
# Returns the full JSON representation of the notification list on success.
'''

import copy  # noqa
# import ruamel.yaml as yaml, import json - assume these are handled by environment or base class

try:
    from ansible.module_utils.ns1 import NS1ModuleBase
except ImportError:
    from module_utils.ns1 import NS1ModuleBase  # noqa

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    pass

# --- Monitor Keys Map is simpler for notify lists ---
NOTIFY_LIST_KEYS_MAP = dict(
    name=dict(appendable=False),
    notify_list=dict(appendable=False), # The list of recipients/channels
)


class NS1NotifierList(NS1ModuleBase):
    def __init__(self):
        # NOTE: Arguments must be in the same order as documentation for readability
        self.module_arg_spec = dict(
            apiKey=dict(required=True, type='str'),
            state=dict(required=False, type='str', default='present', choices=['present', 'absent']),
            name=dict(required=True, type='str'),
            notify_list=dict(
                required=True,
                type='list',
                elements='dict',
                options=dict(
                    type=dict(required=True, type='str'),
                    config=dict(required=True, type='dict')
                )
            ),
        )
        NS1ModuleBase.__init__(self, self.module_arg_spec, supports_check_mode=True)

    def api_params(self):
        """Prepares API arguments from module parameters."""
        params = dict(
            (key, self.module.params.get(key))
            for key in NOTIFY_LIST_KEYS_MAP
            if self.module.params.get(key) is not None
        )
        return params

    def get_list(self):
        """Loads an existing notification list by name and returns the raw data (dict)."""
        # The NS1 SDK exposes the notify lists via ns1.notifylists()
        try:
            # We list all lists to find the ID since we only have the name.
            lists = self.ns1.notifylists().list()
            for list_data in lists:
                if list_data.get('name') == self.module.params.get('name'):
                    # Retrieve method for NotifyLists also returns the raw dict data
                    return self.ns1.notifylists().retrieve(list_data.get('id'))
            return None # List not found
            
        except ResourceException as re:
            self.module.fail_json(msg="Error retrieving notification lists: %s" % re.message)

    def sanitize_list(self, list_data):
        """Removes API-generated fields for diffing."""
        
        # Remove system-generated read-only fields
        list_data.pop('id', None)
        list_data.pop('created_at', None)
        list_data.pop('updated_at', None)
        list_data.pop('created_by', None)
        list_data.pop('updated_by', None)
        
        return list_data

    def create_list(self):
        """Handles creating a new notification list."""
        
        # Assemble the body based on the API requirements
        body = {
            'name': self.module.params.get('name'),
            'notify_list': self.module.params.get('notify_list')
        }
        
        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Notification list would be created.")

        try:
            list_obj = self.ns1.notifylists().create(body)
        except Exception as e:
            self.module.fail_json(msg="NS1 API list creation failed: %s" % str(e))
        
        return list_obj

    def update_list(self, current_list):
        """Handles updating an existing notification list."""
        
        current_data = self.sanitize_list(copy.deepcopy(current_list))
        
        # Assemble the desired payload for comparison
        desired_payload = self.sanitize_list({
            'name': self.module.params.get('name'),
            'notify_list': self.module.params.get('notify_list')
        })

        # Check for structural changes
        if desired_payload == current_data:
            self.module.exit_json(changed=False, list=current_list)

        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Notification list would be updated.")
            
        list_id = current_list.get('id')
        
        try:
            # NS1 API update requires the ID in the URL and the body payload
            list_obj = self.ns1.notifylists().update(list_id, desired_payload)
        except Exception as e:
            self.module.fail_json(msg="NS1 API list update failed: %s" % str(e))
            
        return list_obj


    def exec_module(self):
        """Entry point for the module."""
        state = self.module.params.get('state')
        list_obj = self.get_list() # Returns raw dictionary data or None

        if state == "absent":
            if list_obj:
                if self.module.check_mode:
                    self.module.exit_json(changed=True, msg="Notification list would be deleted.")
                
                list_id = list_obj.get('id')
                self.ns1.notifylists().delete(list_id)
                self.module.exit_json(changed=True, msg="Notification list deleted.")
            else:
                self.module.exit_json(changed=False, msg="Notification list already absent.")

        # state == "present"
        if list_obj:
            # List found, update it
            try:
                list_data = self.update_list(list_obj)
                self.module.exit_json(changed=True, job=list_data)
            except Exception as e:
                self.module.fail_json(msg="Failed to update notification list: %s" % str(e))
        else:
            # List not found, create it
            try:
                list_data = self.create_list()
                self.module.exit_json(changed=True, job=list_data)
            except Exception as e:
                self.module.fail_json(msg="Failed to create notification list: %s" % str(e))


def main():
    list_module = NS1NotifierList()
    list_module.exec_module()


if __name__ == '__main__':
    main()
