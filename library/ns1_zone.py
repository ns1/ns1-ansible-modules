#!/usr/bin/python

# Copyright: (c) 2019, Matthew Burtless <mburtless@ns1.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


from ansible.module_utils.ns1 import NS1ModuleBase, HAS_NS1
ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
---
module: ns1_zone

short_description: Create, modify and delete NS1 hosted zones.

version_added: "2.9"

description:
  - Create, modify and delete zone objects.

options:
  state:
    description:
      - Whether the zone should be present or not.  Use C(present) to create
        or update and C(absent) to delete.
    type: str
    default: present
    choices:
      - absent
      - present
  name:
    description:
      - The domain of the zone.
    type: str
    required: true
  refresh:
    description:
      - The Refresh TTL value used in the SOA for the zone.
    type: int
    required: false
  retry:
    description:
      - The Retry TTL value used in the SOA for the zone.
    type: int
    required: false
    default: None
  expiry:
    description:
      - The Expiry TTL value used in the SOA for the zone.
    type: int
    required: false
    default: None
  nx_ttl:
    description:
      - The NX TTL value used in the SOA for the zone.
    type: int
    required: false
    default: None
  ttl:
   description:
      - The SOA TTL value used in the SOA for the zone.
    type: int
    required: false
    default: None
  dnssec:
    description:
      - Whether dnssec should be enabled for this zone
    type: bool
    required: false
    default: None
  link:
    description:
      - The domain this zone should be linked to. If you specify link only
        name, state and apiKey are allowed.
    type: str
    required: false
    default: None
  networks:
    description:
      - If your account has access to multiple DNS networks, you may pass in
        networks, a list of network ids for which the zone should be made
        available.
    type: list
    required: false
    default: None
  secondary:
    description:
      - To create a secondary zone, you must include a secondary object.
    type: dict
    required: false
    default: None
    suboptions:
      enabled:
        description:
          - If true the zone is configured as a secondary zone.
        type: bool
        required: false
      primary_ip:
        description:
          - An IPv4 address, not a hostname, for the primary DNS server for the zone.
        type: str
        required: false
      primary_port:
        description:
          - Port of primary DNS server.  Only include if not running on standard port.
        type: int
        required: false
  primary:
    description:
      - To enable slaving of your zone by third party DNS servers,
        you must include a primary object.
    type: str
    required: false
    default: None

extends_documentation_fragment:
  - ns1

author:
  - 'Matthew Burtless (@mburtless)'
'''
EXAMPLES = '''
  - name: create zone
    local_action:
      module: ns1_zone
      apiKey: "{{ key }}"
      name: "{{ test_zone }}"
      state: present
      refresh: 200
    register: return

  - name: delete zone
    local_action:
      module: ns1_zone
      apiKey: "{{ key }}"
      name: "{{ test_zone }}"
      state: absent
    register: return
'''

RETURN = '''
'''


try:
    from ns1 import NS1, Config
    from ns1.rest.errors import ResourceException
except ImportError:
    # This is handled in NS1 module_utils
    pass

SECONDARY_KEYS = [
  'enabled',
  'primary_ip',
  'primary_port',
  'other_ips',
  'other_ports',
]

ZONE_KEYS = [
    'refresh',
    'retry',
    'expiry',
    'nx_ttl',
    'ttl',
    'link',
    'networks',
    'secondary',
    'secondary_enabled',
    'primary_ip',
    'primary_port',
    'primary',
    'primary_enabled',
    'secondaries',
    'dnssec'
]


class NS1Zone(NS1ModuleBase):
    def __init__(self):
        self.module_arg_spec = dict(
            name=dict(required=True, type='str'),
            refresh=dict(required=False, type='int', default=None),
            retry=dict(required=False, type='int', default=None),
            expiry=dict(required=False, type='int', default=None),
            nx_ttl=dict(required=False, type='int', default=None),
            ttl=dict(required=False, type='int', default=None),
            link=dict(required=False, type='str', default=None),
            networks=dict(required=False, type='list', default=None),
            secondary=dict(
                required=False,
                type='dict',
                default=None,
                options=dict(
                    enabled=dict(type='bool', default=False),
                    primary_ip=dict(required=False, type='str', default=None),
                    primary_port=dict(required=False, type='int', default=None),
                ),
            ),
            primary=dict(required=False, type='str', default=None),
            dnssec=dict(required=False, type='bool', default=None),
            state=dict(
                required=False,
                type='str',
                default='present',
                choices=['present', 'absent'],
            ),
        )
        self.mutually_exclusive = [
            ['link', 'networks'],
            ['link', 'retry'],
            ['link', 'expiry'],
            ['link', 'nx_ttl'],
            ['link', 'ttl'],
            ['link', 'secondary'],
            ['link', 'primary'],
            ['link', 'refresh']
        ]

        NS1ModuleBase.__init__(self, self.module_arg_spec,
                               supports_check_mode=True,
                               mutually_exclusive=self.mutually_exclusive)
        self.exec_module()

    def remove_empty_subparams(self, param_val):
        if isinstance(param_val, dict):
            return dict(
                (key, value)
                for key, value in param_val.items()
                if value is not None
            )
        return param_val

    def api_params(self):
        params = {}
        for key in ZONE_KEYS:
            param_val = self.module.params.get(key)
            if param_val is not None:
                if isinstance(param_val, dict):
                    params[key] = self.remove_empty_subparams(param_val)
                else:
                    params[key] = param_val

        return params

    def get_zone(self):
        zone = None
        try:
            zone = self.ns1.loadZone(self.module.params.get('name'))
        except ResourceException as re:
            if re.response.code != 404:
                module.fail_json(
                    msg="error code %s - %s " % (re.response.code, re.message)
                )
                zone = None
        return zone

    def key_changed(self, param_key, param_val, zone_data):
        if param_val is not None and (
            not zone_data
            or param_key not in zone_data
            or param_val != zone_data[param_key]
        ):
            return True

        return False

    def secondary_changed(self, secondary, zone_data):
        changed = False
        secondary_args = {}

        # no change if secondary doesn't exist or is empty
        if secondary is None or not bool(secondary):
            return False, secondary_args

        # if zone was not previously a secondary, this must be a change
        if "secondary" not in zone_data:
            return True, self.remove_empty_subparams(secondary)

        for key in SECONDARY_KEYS:
            if key in secondary and self.key_changed(
                key, secondary[key], zone_data["secondary"]
            ):
                changed = True
                secondary_args[key] = secondary[key]

        return changed, secondary_args

    def update(self, zone):
        changed = False
        args = {}

        for key in ZONE_KEYS:
            param_val = self.module.params.get(key)
            if key == "secondary":
                found_change, secondary_args = self.secondary_changed(
                    param_val, zone.data
                )
                if found_change:
                    changed = True
                    args["secondary"] = secondary_args
            if key != "secondary" and self.key_changed(
                key, param_val, zone.data
            ):
                changed = True
                args[key] = param_val

        if self.module.check_mode:
            # check mode short circuit before update
            self.module.exit_json(changed=changed)

        if changed:
            # update only if changed
            zone = zone.update(errback=self.errback_generator(), **args)

        self.module.exit_json(changed=changed, id=zone['id'], data=zone.data)

    def exec_module(self):
        state = self.module.params.get('state')
        zone = self.get_zone()

        # zone found
        if zone:
            if state == "absent":
                if self.module.check_mode:
                    # short circut in check mode
                    self.module.exit_json(changed=True)

                zone.delete(errback=self.errback_generator())
                self.module.exit_json(changed=True)
            else:
                self.update(zone)
        else:
            if state == "absent":
                self.module.exit_json(changed=False)
            else:
                if self.module.check_mode:
                    # short circuit in check mode
                    self.module.exit_json(changed=True)
                zone = self.ns1.createZone(
                    self.module.params.get('name'),
                    errback=self.errback_generator(),
                    **self.api_params()
                )
                self.module.exit_json(
                    changed=True, id=zone['id'], data=zone.data)


def main():
    NS1Zone()


if __name__ == '__main__':
    main()
