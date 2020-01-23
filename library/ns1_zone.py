#!/usr/bin/python

# Copyright: (c) 2019, Matthew Burtless <mburtless@ns1.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    from ansible.module_utils.ns1 import NS1ModuleBase, HAS_NS1
except ImportError:
    from module_utils.ns1 import NS1ModuleBase, HAS_NS1 # noqa
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
          - An IPv4 address, not a hostname, for the primary DNS server for
            the zone.
        type: str
        required: false
      primary_port:
        description:
          - Port of primary DNS server.  Only needs to be included if DNS is
            not running on standard port.
        type: int
        required: false
      other_ips:
        description:
          - A list of IPv4 addresses for additional primary DNS servers for
            the zone.
        type: list
        required: false
        default: None
      other_ports:
        description:
          - A list of ports for additional primary DNS servers for the zone.
        type: list
        required: false
        default: None
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
    from ns1.rest.errors import ResourceException
except ImportError:
    # This is handled in NS1 module_utils
    pass


# list of keys that should be treated as set during diff
SET_KEYS = [
    'other_ips',
    'other_ports',
    'networks',
]

# list of keys that should be sanitized before calls to API
SANITIZED_KEYS = [
    'name',
    'apiKey',
    'endpoint',
    'ignore_ssl',
    'state',
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
                    primary_port=dict(
                      required=False,
                      type='int',
                      default=None
                    ),
                    other_ips=dict(required=False, type='list', default=None),
                    other_ports=dict(
                      required=False,
                      type='list',
                      default=None
                    ),
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

    def sanitize_params(self, params):
        sanitized = {}
        for k, v in params.items():
            if isinstance(v, dict):
                v = self.sanitize_params(v)
            if v is not None and k not in SANITIZED_KEYS:
                sanitized[k] = v
        return sanitized

    def get_zone(self):
        zone = None
        try:
            zone = self.ns1.loadZone(self.module.params.get('name'))
        except ResourceException as re:
            if re.response.code != 404:
                self.module.fail_json(
                    msg="error code %s - %s " % (re.response.code, re.message)
                )
                zone = None
        return zone

    def compare_params(self, have, want):
        '''
        compare_zones compares the current zone to the one we want based on
        params.  Returns a diff to use as params in update
        '''
        diff = {}
        for param, value in want.items():
            if param not in have:
                diff[param] = value
                continue
            # if param has subparams, call compare_params on subparam dict
            if isinstance(value, dict):
                subparam_diff = self.compare_params(have[param], value)
                if subparam_diff:
                    diff[param] = subparam_diff
            # if param is list, check if it should be compared as a set
            elif isinstance(value, list) and param in SET_KEYS:
                if set(have[param]) != set(value):
                    diff[param] = value
            # else compare as value
            elif have[param] != value:
                diff[param] = value
        return diff

    def update(self, zone):
        changed = False
        args = {}

        want = self.sanitize_params(self.module.params)
        # compare zone.data and wanted state
        args = self.compare_params(zone.data, want)
        if args:
            changed = True

        if self.module.check_mode:
            # check mode short circuit before update
            self.module.exit_json(changed=changed)

        if changed:
            # update only if changed
            zone = zone.update(errback=self.errback_generator(), **args)

        self.module.exit_json(changed=changed, id=zone['id'], data=zone.data)

    def create(self, zone):
        if self.module.check_mode:
            # short circuit in check mode
            self.module.exit_json(changed=True)

        zone = self.ns1.createZone(
            self.module.params.get('name'),
            errback=self.errback_generator(),
            **self.sanitize_params(self.module.params)
        )
        self.module.exit_json(
            changed=True, id=zone['id'], data=zone.data)

    def delete(self, zone):
        if self.module.check_mode:
            # short circut in check mode
            self.module.exit_json(changed=True)
        zone.delete(errback=self.errback_generator())
        self.module.exit_json(changed=True)

    def exec_module(self):
        state = self.module.params.get('state')
        zone = self.get_zone()
        if state == "present":
            self.present(zone)
        if state == "absent":
            self.absent(zone)

    def present(self, zone):
        if zone:
            self.update(zone)
        else:
            self.create(zone)

    def absent(self, zone):
        if zone:
            self.delete(zone)
        else:
            self.module.exit_json(changed=False)


def main():
    z = NS1Zone()
    z.exec_module()


if __name__ == '__main__':
    main()
