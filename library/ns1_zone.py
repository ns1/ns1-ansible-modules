
#!/usr/bin/python
# Copyright: (c) 2020, NS1
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
      tsig:
        description:
          - Used to configure TSIG authentication on a secondary zone
        type: dict
        required: false
        default: None
        suboptions:
          enabled:
            description:
            - If true TSIG authentication is enabled for the secondary zone.
            type: bool
            required: false
          hash:
            description:
            - The type of hash to use (i.e. hmac-sha256).
            - Required if TSIG is enabled.
            type: str
            required: false
          key:
            description:
            - The pre-shared TSIG key.
            - Required if TSIG is enabled.
            type: str
            required: false
          name:
            description:
            - The name of the key.
            - Required if TSIG is enabled.
            type: str
            required: false
  primary:
    description:
      - To enable slaving of your zone by third party DNS servers,
        you must include a primary object.
    type: dict
    required: false
    default: None
    suboptions:
      enabled:
        description:
          - If true the zone is enabled for outgoing zone transfers.
        type: bool
        required: false
      secondaries:
        description:
          - Collection of secondary DNS servers that slave off this zone.
        type: list
        required: false
        suboptions:
          ip:
            description:
              - The IPv4 address of the secondary DNS server.
            type: str
          port:
            description:
              - The port on the secondary server to send NOTIFY messages
            type: int
            required: false
          notify:
            description:
              - Whether or not NS1 should send NOTIFY messages to the host
                when the zone changes
            type: bool

requirements:
  - python >= 2.7
  - ns1-python >= 0.9.19

seealso:
  - name: Documentation for NS1 API
    description: Complete reference for the NS1 API.
    link: https://ns1.com/api/

author:
  - 'NS1'
"""

EXAMPLES = r"""
- name: create zone
  local_action:
    module: ns1_zone
    apiKey: "{{ ns1_token }}"
    name: test.com
    state: present
    refresh: 200
  register: return

- name: delete zone
  local_action:
    module: ns1_zone
    apiKey: "{{ ns1_token }}"
    name: test.com
    state: absent
  register: return
"""

RETURN = r"""
"""

import functools  # noqa

import ruamel.yaml as yaml

try:
    from ansible.module_utils.ns1 import NS1ModuleBase, HAS_NS1, Decorators
except ImportError:
    # import via absolute path when running via pytest
    from module_utils.ns1 import NS1ModuleBase, HAS_NS1, Decorators  # noqa

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
    "state",
    "name",
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
                    tsig=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            enabled=dict(type="bool", default=None),
                            hash=dict(type="str", default=None),
                            key=dict(type="str", default=None),
                            name=dict(type="str", default=None),
                        ),
                    ),
                ),
            ),
            primary=dict(
                required=False,
                type="dict",
                default=None,
                options=dict(
                    enabled=dict(type="bool", default=None),
                    secondaries=dict(
                        type="list",
                        default=None,
                        options=dict(
                            ip=dict(type="str", default=None),
                            port=dict(
                                required=False, type="int", default=None
                            ),
                            notify=dict(
                                required=False, type="bool", default=None
                            ),
                        ),
                    ),
                ),
            ),
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

    def sanitize_params(self, params):
        """Removes fields from Ansible module parameters that have no value
        or are listed in SANITIZED_PARAMS

        :param params: Ansible module parameters
        :type params: dict
        :return: Sanitized dict of params
        :rtype: dict
        """

        def filter_empty_params(d):
            filtered = {}
            for key, val in d.items():
                if isinstance(val, dict):
                    nested = filter_empty_params(val)
                    if nested:
                        filtered[key] = nested
                elif val is not None:
                    filtered[key] = val
            return filtered

        params = filter_empty_params(params)
        # remove sanitized params from top level
        for param in SANITIZED_PARAMS:
            params.pop(param, None)
        return params

    def get_zone(self, name):
        """Retrieves a zone from NS1. If no name is given or zone does not
        exist, will return None.

        :param name: Name of the zone to retrieve
        :type name: str, optional
        :return: zone object returned by NS1
        :rtype: ns1.zones.Zone
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

    def diff_params(self, have, want):
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
                subparam_diff = self.diff_params(have[param], wanted_val)
                if subparam_diff:
                    diff[param] = subparam_diff
            elif isinstance(wanted_val, list) and param in SET_PARAMS:
                if set(have[param]) != set(wanted_val):
                    diff[param] = wanted_val
            elif have[param] != wanted_val:
                diff[param] = wanted_val
        return diff

    def get_changed_params(self, have, want):
        """Gets Ansible params in want that have changed from have

        :param have: Existing set of parameters
        :type have: dict
        :param want: Desired end state of parameters
        :type want: dict
        :return: Parameters in want that differ from have
        :rtype: tuple(dict, dict)
        """
        diff = self.diff_params(have, want)

        # perform deep comparison of secondaries if primary exists and has diff
        if "primary" in have and "primary" in diff:
            have_secondaries = have["primary"].get("secondaries")
            want_secondaries = want["primary"].get("secondaries")

            # if no difference in values, remove secondaries from diff results
            if not self.diff_in_secondaries(
                have_secondaries, want_secondaries
            ):
                diff["primary"].pop("secondaries", None)

                # if secondaries was only key in primary, remove primary
                if not diff["primary"]:
                    diff.pop("primary", None)

        if self.module._diff:

            # build after dict from have with updated changes
            after = {}
            for param in have:
                if param not in diff:
                    after[param] = have[param]
                else:
                    after[param] = diff[param]

            # convert dictionaries to yaml txt dump
            have_yaml = yaml.safe_dump(have, default_flow_style=False)
            diff_yaml = yaml.safe_dump(after, default_flow_style=False)

            # build diff from different yaml dumps
            result_diff = dict(
                before=have_yaml,
                after=diff_yaml
            )
            return result_diff, diff

        else:
            return {}, diff

    def diff_in_secondaries(self, have_secondaries, want_secondaries):
        """Performs deep comparison of two lists of secondaries, ignoring order.

        :param have_secondaries: Existing secondaries list
        :type have_secondaries: list
        :param want_secondaries: Desired end state of secondaries list
        :type want_secondaries: list
        :return: Whether or not there is a difference between the lists
        :rtype: bool
        """
        if want_secondaries is None:
            # if no secondaries provided in params, no change
            return False
        elif have_secondaries is None:
            # if no secondaries were already set, will be a change
            return True
        elif len(want_secondaries) != len(have_secondaries):
            return True

        have = self.convert_secondaries_to_dict(have_secondaries)
        want = self.convert_secondaries_to_dict(want_secondaries)
        diff = self.diff_params(have, want)
        if diff:
            return True

        return False

    def convert_secondaries_to_dict(self, secondaries):
        """Converts a secondaries list to a dictionary. Keys are a tuple of
        of IP and Port fields.

        :param secondaries: List of secondary dicts
        :type secondaries: list
        :return: Dict of secondary dicts
        :rtype: dict
        """
        try:
            return {(s["ip"], s["port"]): s for s in secondaries}
        except KeyError as ke:
            self.module.fail_json(
                msg="missing field in secondary definition: {0}".format(ke)
            )

    @Decorators.skip_in_check_mode
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

    @Decorators.skip_in_check_mode
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

    @Decorators.skip_in_check_mode
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
            changed, zone, diff = self.present(zone)
        if state == "absent":
            changed = self.absent(zone)
            zone = {}
            diff = {}
        return self.build_result(changed, zone, diff)

    def present(self, zone):
        """Handles use case where desired state of zone is present.
        If zone is provided, it is updated with params from Ansible that
        differ from existing values. If zone is not provided, a new zone will
        be created with params from Ansible.

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict, optional
        :return: Tuple in which first value reflects whether or not a change
        occured and second value is new or updated zone object
        :rtype: tuple(bool, dict, dict)
        """
        want = self.sanitize_params(self.module.params)
        if zone:
            # only if zone already exists
            return self.update_on_change(zone, want)
        else:
            # only if zone does not exist
            for param, value in self.module.params.items():
                if param not in want:
                    want[param] = value
                else:
                    if want[param] != value:
                        want[param] = value
            changed_params = {
                "before": {},
                "after": want
            }
            return True, self.create(want), changed_params

    def update_on_change(self, zone, want):
        """triggers update of zone if diff between zone and desired state in want

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict
        :param want: Desired state of zone
        :type want: dict
        :return: Tuple in which first value reflects whether or not a change
        occured and second value is new or updated zone object
        :rtype: tuple(bool, dict, dict)
        """
        changed_params, diff = self.get_changed_params(zone.data, want)
        if diff and not self.module.check_mode:
            return True, self.update(zone, diff), changed_params
        elif diff and self.module.check_mode:
            return True, zone, changed_params
        return False, zone, changed_params

    def absent(self, zone):
        """Handles use case where desired state of zone is absent.
        If zone is provided, it is deleted.

        :param zone: Zone object of existing zone returned by NS1
        :type zone: dict, optional
        :return: Whether or not a change occured
        :rtype: bool
        """
        if zone:
            self.delete(zone)
            return True

        return False

    def build_result(self, changed, zone, diff):
        """Builds dict of results from module execution to pass to module.exit_json()

        :param changed: Whether or not a change occured
        :type changed: bool
        :param zone: Zone object returned by NS1 of new or updated zone
        :type zone: dict
        :return: Results of module execution
        :rtype: dict
        """
        result = {"changed": changed}

        if diff and self.module._diff:
            result["diff"] = diff

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
