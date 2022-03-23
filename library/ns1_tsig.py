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
module: ns1_tsig

short_description: Create, modify and delete NS1 hosted tsigs.

version_added: "2.9"

description:
  - Create, modify and delete tsig objects.

options:
  apiKey:
    description:
      - Unique client api key that can be created via the NS1 portal.
    type: str
    required: true
  key_name:
    description:
      - The unique name of the tsig.
    type: str
    required: true
  algorithm:
    description:
      - The algorithm used in tsig
    type: str
    required: true
    choices:
      - hmac-sha1
      - hmac-sha224
      - hmac-sha256
      - hmac-sha384
      - hmac-sha512
      - hmac-md5
  secret:
    description:
      - the secret used in tsig must be in base64
    type: str
    required: true
  state:
    description:
      - Whether the tsig should be present or not.  Use C(present) to create
        or update and C(absent) to delete.
    type: str
    choices:
      - absent
      - present
      
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
- name: create tsig
  local_action:
    module: ns1_tsig
    apiKey: "{{ ns1_token }}"
    key_name: "MyTsig"
    algorithm: "hmac-sha256"
    secret: "c2VjcmV0Mg=="
    state: absent
    
- name: update tsig
  local_action:
    module: ns1_tsig
    key_name: "MyTsig"
    algorithm: "hmac-sha256"
    secret: "hmac-sha512"
    state: present
    
- name: Delete tsig
  local_action:
    module: ns1_tsig
    apiKey: "{{ ns1_token }}"
    key_name: "{{ keyname }}"
    state: absent
"""

RETURN = r"""
"""

import functools  # noqa

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


class NS1Tsig(NS1ModuleBase):
    """Represents the NS1 tsig module implementation
    """

    def __init__(self):
        """Constructor method
        """
        self.module_arg_spec = dict(
            key_name=dict(required=False, type='str', default="defaultName"),
            algorithm=dict(required=False, type='str', default="defaultAlgo"),
            secret=dict(required=False, type='str', default="defaultSecret"),
            state=dict(
                required=False,
                type="str",
                default="present",
                choices=["present", "absent"],
            )
        )

        NS1ModuleBase.__init__(self,
                               self.module_arg_spec,
                               supports_check_mode=True)

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

    def get_tsig(self, name):
        """Retrieves a tsig from NS1. If no name is given or tsig does not
        exist, will return None.

        :param name: Name of the tsig to retrieve
        :type name: str, optional
        :return: tsig object returned by NS1
        :rtype: ns1.tsig.Tsig
        """
        tsig = None
        if name:
            try:
                tsig_client = self.ns1.tsig()
                tsig = tsig_client.retrieve(name)
            except ResourceException as re:
                if re.response.code != 404:
                    self.module.fail_json(
                        msg="error code %s - %s "
                            % (re.response.code, re.message)
                    )
                    tsig = None
        return tsig

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
        :rtype: dict
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
        return diff

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
    def update(self, args):
        """Updates the tsig in NS1 with values from args

        :param args: Dict of args and values to update the tsig with
        :type args: dict
        :return: The updated tsig object returned by NS1
        :rtype: dict
        """
        tsig_client = self.ns1.tsig()
        return tsig_client.update(errback=self.errback_generator(), **args)

    @Decorators.skip_in_check_mode
    def create(self, args):
        """Creates a tsig in NS1 with the given args.

        :param args: Dict of args and values to update the tsig with
        :type args: dict
        :return: [description]
        :rtype: [type]
        """
        tsig_client = self.ns1.tsig()
        return tsig_client.create(
            errback=self.errback_generator(),
            **args
        )

    @Decorators.skip_in_check_mode
    def delete(self, tsig):
        """Deletes a tsig in NS1.

        :param tsig: tsig object of existing tsig returned by NS1
        :type tsig: dict
        """
        tsig_client = self.ns1.tsig()
        tsig_client.delete(tsig["name"], errback=self.errback_generator())

    def exec_module(self):
        """Main execution method of module.  Creates, updates or deletes a
        tsig based on Ansible parameters.

        :return: Results of module execution
        :rtype: dict
        """

        changed = False
        state = self.module.params.get("state")
        tsig = self.get_tsig(self.module.params.get("key_name"))

        if state == "present":
            changed, tsig = self.present(tsig)
        if state == "absent":
            changed = self.absent(tsig)
            tsig = {}
        return self.build_result(changed, tsig)

    def present(self, tsig):
        """Handles use case where desired state of tsig is present.
        If tsig is provided, it is updated with params from Ansible that
        differ from existing values. If tsig is not provided, a new tsig will
        be created with params from Ansible.

        :param tsig: tsig object of existing tsig returned by NS1
        :type tsig: dict, optional
        :return: Tuple in which first value reflects whether or not a change
        occured and second value is new or updated tsig object
        :rtype: tuple(bool, dict)
        """
        want = self.sanitize_params(self.module.params)
        if tsig:
            return self.update_on_change(tsig, want)
        return True, self.create(want)

    def update_on_change(self, tsig, want):
        """triggers update of tsig if diff between tsig and desired state in want

        :param tsig: tsig object of existing tsig returned by NS1
        :type tsig: dict
        :param want: Desired state of tsig
        :type want: dict
        :return: Tuple in which first value reflects whether or not a change
        occured and second value is new or updated tsig object
        :rtype: tuple(bool, dict)
        """
        changed_params = self.get_changed_params(tsig, want)
        if changed_params:
            return True, self.update(changed_params)
        return False, tsig

    def absent(self, tsig):
        """Handles use case where desired state of tsig is absent.
        If tsig is provided, it is deleted.

        :param tsig: tsig object of existing tsig returned by NS1
        :type tsig: dict, optional
        :return: Whether or not a change occured
        :rtype: bool
        """

        if tsig:
            self.delete(tsig)
            return True
        return False

    def build_result(self, changed, tsig):
        """Builds dict of results from module execution to pass to module.exit_json()

        :param changed: Whether or not a change occured
        :type changed: bool
        :param tsig: tsig object returned by NS1 of new or updated tsig
        :type tsig: dict
        :return: Results of module execution
        :rtype: dict
        """
        result = {"changed": changed}
        if tsig and not self.module.check_mode:
            result["name"] = tsig["name"]
            result["secret"] = tsig["secret"]
            result["algorithm"] = tsig["algorithm"]
        return result


def main():
    z = NS1Tsig()
    result = z.exec_module()
    z.module.exit_json(**result)


if __name__ == "__main__":
    main()
