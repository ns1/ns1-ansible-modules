#!/usr/bin/python

# Copyright: (c) 2019, NS1
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
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
"""

EXAMPLES = r"""
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
"""

RETURN = r"""
"""

import functools  # noqa

try:
    from ansible.module_utils.ns1 import NS1ModuleBase, HAS_NS1
except ImportError:
    # import via absolute path when running via pytest
    from module_utils.ns1 import NS1ModuleBase, HAS_NS1  # noqa

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    # This is handled in NS1 module_utils
    pass


# list of params that should be treated as set during diff
SET_PARAMS = [
    "other_ips",
    "other_ports",
    "networks",
]

# list of params that should be removed before calls to API
SANITIZED_PARAMS = [
    "name",
    "apiKey",
    "endpoint",
    "ignore_ssl",
    "state",
]


class NS1Zone(NS1ModuleBase):
    """Represents the NS1 Zone module implementation
    """

    def __init__(self):
        """Constructor method
        """
        self.module_arg_spec = dict(
            name=dict(required=True, type="str"),
            refresh=dict(required=False, type="int", default=None),
            retry=dict(required=False, type="int", default=None),
            expiry=dict(required=False, type="int", default=None),
            nx_ttl=dict(required=False, type="int", default=None),
            ttl=dict(required=False, type="int", default=None),
            link=dict(required=False, type="str", default=None),
            networks=dict(required=False, type="list", default=None),
            secondary=dict(
                required=False,
                type="dict",
                default=None,
                options=dict(
                    enabled=dict(type="bool", default=False),
                    primary_ip=dict(required=False, type="str", default=None),
                    primary_port=dict(
                        required=False, type="int", default=None
                    ),
                    other_ips=dict(required=False, type="list", default=None),
                    other_ports=dict(
                        required=False, type="list", default=None
                    ),
                ),
            ),
            primary=dict(required=False, type="str", default=None),
            dnssec=dict(required=False, type="bool", default=None),
            state=dict(
                required=False,
                type="str",
                default="present",
                choices=["present", "absent"],
            ),
        )
        self.mutually_exclusive = [
            ["link", "networks"],
            ["link", "retry"],
            ["link", "expiry"],
            ["link", "nx_ttl"],
            ["link", "ttl"],
            ["link", "secondary"],
            ["link", "primary"],
            ["link", "refresh"],
        ]

        NS1ModuleBase.__init__(
            self,
            self.module_arg_spec,
            supports_check_mode=True,
            mutually_exclusive=self.mutually_exclusive,
        )

    def skip_in_check_mode(func):
        """Decorater function that skips passed function if module is
        in check_mode.  If module is not in check_mode, passed function
        executes normally.

        :param func: Function to wrap
        :type func: func
        :return: Wrapped function
        :rtype: func
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.module.check_mode:
                return
            return func(self, *args, **kwargs)

        return wrapper

    def sanitize_params(self, params):
        """Removes all Ansible module parameters from dict that have no value
        or are listed in SANITIZED_PARAMS

        :param params: Ansible module parameters
        :type params: dict
        :return: Sanitized dict of params
        :rtype: dict
        """
        sanitized = {}
        for k, v in params.items():
            if isinstance(v, dict):
                v = self.sanitize_params(v)
            if v is not None and k not in SANITIZED_PARAMS:
                sanitized[k] = v
        return sanitized

    def get_zone(self, name):
        """Retrieves a zone from NS1. If no name is given or zone does not
        exist, will return None.

        :param name: Name of the zone to retrieve
        :type name: str, optional
        :return: zone object returned by NS1
        :rtype: dict
        """
        zone = None
        if name:
            try:
                zone = self.ns1.loadZone(name)
            except ResourceException as re:
                if re.response.code != 404:
                    self.module.fail_json(
                        msg="error code %s - %s "
                        % (re.response.code, re.message)
                    )
                    zone = None
        return zone

    def compare_params(self, have, want):
        """Performs deep comparison of two sets of Ansible parameters. Returns
        values from want that differ from have.

        :param have: Existing set of parameters
        :type have: dict
        :param want: Desired end state of parameters
        :type want: dict
        :return: Parameters in want that differ from have
        :rtype: dict
        """
        diff = {}
        for param, wanted_val in want.items():
            if param not in have:
                diff[param] = wanted_val
                continue
            if isinstance(wanted_val, dict):
                subparam_diff = self.compare_params(have[param], wanted_val)
                if subparam_diff:
                    diff[param] = subparam_diff
            elif isinstance(wanted_val, list) and param in SET_PARAMS:
                if set(have[param]) != set(wanted_val):
                    diff[param] = wanted_val
            elif have[param] != wanted_val:
                diff[param] = wanted_val
        return diff

    @skip_in_check_mode
    def update(self, zone, args):
        """Updates the zone in NS1 with values from args

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict
        :param args: Dict of args and values to update the zone with
        :type args: dict
        :return: The updated zone object returned by NS1
        :rtype: dict
        """
        return zone.update(errback=self.errback_generator(), **args)

    @skip_in_check_mode
    def create(self, args):
        """Creates a zone in NS1 with the given args.

        :param args: Dict of args and values to update the zone with
        :type args: dict
        :return: [description]
        :rtype: [type]
        """
        return self.ns1.createZone(
            self.module.params.get("name"),
            errback=self.errback_generator(),
            **args
        )

    @skip_in_check_mode
    def delete(self, zone):
        """Deletes a zone in NS1.

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict
        """
        zone.delete(errback=self.errback_generator())

    def exec_module(self):
        """Main execution method of module.  Creates, updates or deletes a
        zone based on Ansible parameters.

        :return: Results of module execution
        :rtype: dict
        """
        changed = False
        state = self.module.params.get("state")
        zone = self.get_zone(self.module.params.get("name"))
        if state == "present":
            changed, zone = self.present(zone)
        if state == "absent":
            changed = self.absent(zone)
        return self.build_result(changed, zone)

    def present(self, zone):
        """Handles use case where desired state of zone is present.
        If zone is provided, it is updated with params from Ansible that
        differ from existing values. If zone is not provided, a new zone will
        be created with params from Ansible.

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict, optional
        :return: Tuple in which first value reflects whether or not a change
        occured and second value is new or updated zone object
        :rtype: tuple(bool, dict)
        """
        changed = False
        want = self.sanitize_params(self.module.params)
        if zone:
            diff = self.compare_params(zone.data, want)
            if diff:
                changed = True
                zone = self.update(zone, diff)
        else:
            changed = True
            zone = self.create(want)
        return changed, zone

    def absent(self, zone):
        """Handles use case where desired state of zone is absent.
        If zone is provided, it is deleted.

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict, optional
        :return: Whether or not a change occured
        :rtype: bool
        """
        changed = False
        if zone:
            changed = True
            self.delete(zone)

        return changed

    def build_result(self, changed, zone):
        """Builds dict of results from module execution to pass to module.exit_json()

        :param changed: Whether or not a change occured
        :type changed: bool
        :param zone: Zone object returned by NS1 of new or updated zone
        :type zone: dict
        :return: Results of module execution
        :rtype: dict
        """
        result = {"changed": changed}
        if zone and not self.module.check_mode:
            result["id"] = zone["id"]
            result["zone"] = zone.data
        return result


def main():
    z = NS1Zone()
    result = z.exec_module()
    z.module.exit_json(**result)


if __name__ == "__main__":
    main()
