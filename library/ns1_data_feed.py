#!/usr/bin/python

# Copyright: (c) 2025, Michael Kearey
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
module: ns1_data_feed

short_description: Create and manage NS1 Data Feeds (connections from a Data Source).

version_added: "2.10"

description:
  - Manages a specific Data Feed resource, linking a Data Source (e.g., a Monitor)
    to the DNS platform. Requires the parent source ID and unique feed configuration.

options:
  apiKey:
    description:
      - Unique client API key.
    type: str
    required: true
  state:
    description:
      - Whether the data feed should be C(present) or C(absent).
    type: str
    default: present
    choices:
      - absent
      - present
  source_id:
    description:
      - The unique ID of the parent Data Source (e.g., '__NS1__.data_source.monitoring.0').
    type: str
    required: true
  name:
    description:
      - The unique name of the data feed (e.g., '__NS1__...rhcoresite.vpn.neuralmagic.com-943').
    type: str
    required: true
  config:
    description:
      - Dictionary of feed-specific configuration, often including the 'jobid' of the associated monitor.
    type: dict
    required: true
'''

EXAMPLES = '''
- name: Create Data Feed for a specific monitor job
  ns1_data_feed:
    apiKey: "{{ ns1_token }}"
    state: present
    source_id: "{{ MONITOR_SOURCE_ID }}"
    name: "__NS1__.data_feed.monitoring.my-site-80"
    config:
      jobid: "68e46785142c1200014d87d9" # ID of the monitoring job
'''

RETURN = '''
# Returns the full JSON representation of the data feed on success.
'''

import copy # noqa
import json # noqa

try:
    from ansible.module_utils.ns1 import NS1ModuleBase
except ImportError:
    from module_utils.ns1 import NS1ModuleBase  # noqa

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    pass

class NS1DataFeed(NS1ModuleBase):
    def __init__(self):
        # We simplify the arg spec since we are only using it for management
        self.module_arg_spec = dict(
            apiKey=dict(required=True, type='str'),
            state=dict(required=False, type='str', default='present', choices=['present', 'absent']),
            source_id=dict(required=True, type='str'),
            name=dict(required=True, type='str'),
            config=dict(required=True, type='dict'),
        )
        NS1ModuleBase.__init__(self, self.module_arg_spec, supports_check_mode=True)

    def get_feed(self, source_id, feed_name):
        """Loads an existing feed by name within a source."""
        try:
            # ns1.datafeed().list() gives a list of feed dicts for a source ID
            feeds = self.ns1.datafeed().list(source_id) 
            for feed_data in feeds:
                if feed_data.get('name') == feed_name:
                    # Retrieve the specific feed object using sourceid and feedid
                    return self.ns1.datafeed().retrieve(source_id, feed_data.get('id'))
            return None
        except ResourceException as re:
            # Fail gracefully if source_id is invalid
            self.module.fail_json(msg="Error listing data feeds for source %s: %s" % (source_id, re.message))

    def create_feed(self, source_id, name, config):
        """Handles creating a new data feed."""
        body = {
            "name": name,
            "config": config,
        }
        
        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Data feed would be created.")

        try:
            # Feed.create() uses PUT /data/feeds/<sourceid>
            feed_obj = self.ns1.datafeed().create(source_id, name, config) 
        except Exception as e:
            self.module.fail_json(msg="NS1 API feed creation failed: %s" % str(e))
        
        return feed_obj

    def delete_feed(self, source_id, feed_id):
        """Handles deleting a data feed."""
        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Data feed would be deleted.")
            
        try:
            self.ns1.datafeed().delete(source_id, feed_id)
        except Exception as e:
            self.module.fail_json(msg="NS1 API feed deletion failed: %s" % str(e))

    def exec_module(self):
        """Entry point for the module."""
        state = self.module.params.get('state')
        source_id = self.module.params.get('source_id')
        name = self.module.params.get('name')
        config = self.module.params.get('config')
        
        # NS1 SDK retrieve() method returns the raw dict data
        feed_data = self.get_feed(source_id, name) 

        if state == "absent":
            if feed_data:
                self.delete_feed(source_id, feed_data.get('id'))
                self.module.exit_json(changed=True, msg="Data feed deleted.")
            else:
                self.module.exit_json(changed=False, msg="Data feed already absent.")

        # state == "present"
        if feed_data:
            # Feed found, check for update (simplification: assume all updates replace)
            self.module.exit_json(changed=False, msg="Data feed present (Update logic simplified).")
        else:
            # Feed not found, create it
            feed_obj = self.create_feed(source_id, name, config)
            self.module.exit_json(changed=True, feed=feed_obj)


def main():
    feed_module = NS1DataFeed()
    feed_module.exec_module()

if __name__ == '__main__':
    main()
