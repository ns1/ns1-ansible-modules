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

short_description: Create, modify and delete NS1 account teams.

version_added: "3.1"

description:
  - Create, modify and delete team objects along with permissions to control access to portal or API.

options:
  apiKey:
    description: Unique client api key that can be created via the NS1 portal.
    type: str
    required: true
  endpoint:
    description: NS1 API endpoint. Defaults to https://api.nsone.net/v1/
    type: str
    required: false
  ignore_ssl:
    description: Whether to ignore SSL errors. Defaults to false
    type: bool
    required: false
  name:
    description: Name of the team being created, updated, or deleted.
    type: str
    required: true
  state:
    description: Whether the team should be present or not.  Use C(present) to create or update and C(absent) to delete.
    type: str
    default: present
    choices:
      - absent
      - present
    required: false
  ip_whitelist:
    description: Array of IP addresses/networks to which to grant the API key access.
    type: list
    required: false
  permissions:
    description: All supported permissions
    type: dict
    required: false
    default: None
    suboptions:
      monitoring:
        description: Group of monitoring-related permissions.
        required: false
        suboptions:
          manage_jobs:
            description: Allows (or prevents, if false) the team to create or modify monitoring jobs.
            type: bool
            default: flase
            required: false
          view_jobs:
            description: Allows (or prevents, if false) the team to view monitoring jobs.
            type: bool
            default: flase
            required: false
          manage_lists:
            description: Allows (or prevents, if false) the team to create or modify notification lists.
            type: bool
            default: flase
            required: false
      account:
        description: Group of account-related permissions.
        required: false
        suboptions:
          manage_users:
            description: Allows (or prevents, if false) the team to create or update users.
            type: bool
            default: flase
            required: false
          view_invoices:
            description: Allows (or prevents, if false) the team to view account invoices.
            type: bool
            default: flase
            required: false
          manage_teams:
            description: Allows (or prevents, if false) the team to create or update teams.
            type: bool
            default: flase
            required: false
          view_activity_log:
            description: Allows (or prevents, if false) the team to view the account activity log.
            type: bool
            default: flase
            required: false
          manage_account_settings:
            description: Allows (or prevents, if false) the team to manage account settings.
            type: bool
            default: flase
            required: false
          manage_apikeys:
            description: Allows (or prevents, if false) the team to create or update API keys.
            type: bool
            default: flase
            required: false
          manage_payment_methods:
            description: Allows (or prevents, if false) the team to manage account payment methods.
            type: bool
            default: flase
            required: false
          manage_ip_whitelist:
            description: Allows (or prevents, if false) the team to create or update IP "allow" lists.
            type: bool
            default: flase
            required: false
      data:
        description: Group of data-related permissions.
        required: false
        suboptions:
          push_to_datafeeds:
            description: Allows (or prevents, if false) the team to push data to NS1 data feeds.
            type: bool
            default: flase
            required: false
          manage_datasources:
            description: Allows (or prevents, if false) the team to create and modify data sources.
            type: bool
            default: flase
            required: false
          manage_datafeeds:
            description: Allows (or prevents, if false) the team to create and modify data feeds.
            type: bool
            default: flase
            required: false
      security:
        description: Group of security-related permissions.
        required: false
        suboptions:
          manage_global_2fa:
            description: Allows (or prevents, if false) the team to manage global two-factor authentication (2FA) settings.
            type: bool
            default: flase
            required: false
      dns:
        description: Group of DNS-related permissions.
        required: false
        suboptions:
          zones_allow:
            description: List of specific zones to which the API key is allowed access.
            type: list
            required: false
          manage_zones:
            description:  Allows (or prevents, if false) the team to create or modify zones.
            type: bool
            default: flase
            required: false
          zones_deny:
            description: List of specific zones to which the team is denied access.
            type: list
            required: false
          view_zones:
            description: Allows (or prevents, if false) the team to view zones.
            type: bool
            default: flase
            required: false
          zones_allow_by_default:
            description: Set to true to allow access to all zones except for those listed under zones_deny. Set to false to deny access to all zones by default except for those listed under zones_allow.
            type: bool
            default: flase
            required: false

requirements:
  - python >= 2.7
  - ns1-python >= 0.16.0

seealso:
  - name: Documentation for NS1 API
    description: Complete reference for the NS1 API.
    link: https://ns1.com/api/

author:
  - 'NS1'
"""

EXAMPLES = r"""
- name: add read only team
  local_action:
    module: ns1_team
    name: RO-Only
    permissions:
      monitoring:
        view_jobs: true
      account:
        view_invoices: true
        view_activity_log: true
      dns:
        view_zones: true

- name: delete team
  local_action:
    module: ns1_team
    apiKey: "{{ ns1_token }}"
    name: NoLongerAdmin
    state: absent
"""

RETURN = r"""
"""

import functools  # noqa
import copy

try:
    from ansible.module_utils.ns1 import NS1ModuleBase, HAS_NS1, Decorators
except ImportError:
    # import via absolute path when running via pytest
    from module_utils.ns1 import NS1ModuleBase, HAS_NS1, Decorators  # noqa

try:
    from ns1.rest.errors import ResourceException
    from ns1.rest.permissions import _default_perms
except ImportError:
    # This is handled in NS1 module_utils
    pass


class NS1Team(NS1ModuleBase):
    """Represents the NS1 Team module implementation"""

    def __init__(self):
        """Constructor method"""
        self.module_arg_spec = dict(
            name=dict(required=True, type="str"),
            ip_whitelist=dict(required=False, type="list", default=None),
            permissions=dict(
                required=False,
                type="dict",
                default=None,
                options=dict(
                    monitoring=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            manage_jobs=dict(type="bool", default=False),
                            view_jobs=dict(type="bool", default=False),
                            manage_lists=dict(type="bool", default=False),
                        ),
                    ),
                    account=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            manage_users=dict(type="bool", default=False),
                            view_invoices=dict(type="bool", default=False),
                            manage_teams=dict(type="bool", default=False),
                            view_activity_log=dict(type="bool", default=False),
                            manage_account_settings=dict(type="bool", default=False),
                            manage_apikeys=dict(type="bool", default=False),
                            manage_payment_methods=dict(type="bool", default=False),
                            manage_ip_whitelist=dict(type="bool", default=False),
                        ),
                    ),
                    data=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            push_to_datafeeds=dict(type="bool", default=False),
                            manage_datasources=dict(type="bool", default=False),
                            manage_datafeeds=dict(type="bool", default=False),
                        ),
                    ),
                    security=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            manage_global_2fa=dict(type="bool", default=False),
                        ),
                    ),
                    dns=dict(
                        required=False,
                        type="dict",
                        default=None,
                        options=dict(
                            zones_allow=dict(type="list", default=False),
                            manage_zones=dict(type="bool", default=False),
                            zones_deny=dict(type="list", default=False),
                            view_zones=dict(type="bool", default=False),
                            zones_allow_by_default=dict(type="bool", default=False),
                        ),
                    ),
                ),
            ),
            state=dict(
                required=False,
                type="str",
                default="present",
                choices=["present", "absent"],
            ),
        )

        NS1ModuleBase.__init__(
            self,
            self.module_arg_spec,
            supports_check_mode=True,
        )

    @Decorators.skip_in_check_mode
    def update(self, team_id, built_changes):
        """Updates a team with permissions from task

        :param team_id: Zone object of existing zone returned by NS1
        :type team_id: str
        :param built_changes: Dict of permissions to be applied to a new
        team.
        :type built_changes: dict
        :return: The updated zone object returned by NS1
        :rtype: dict
        """
        team_update = self.ns1.team()
        return team_update.update(team_id, **built_changes)

    @Decorators.skip_in_check_mode
    def create(self, built_changes):
        """Creates a team with the given permissions.

        :param built_changes: Dict of permissions to be applied to a new
        team.
        :type built_changes: dict
        :return: [description]
        :rtype: [type]
        """
        team_create = self.ns1.team()
        return team_create.create(**built_changes)

    @Decorators.skip_in_check_mode
    def delete(self, team_id):
        """Deletes a team.

        :param team_id: Id of an existing team.
        :type team_id: str
        """
        team_delete = self.ns1.team()
        team_delete.delete(team_id)

    def build_permissions(self):
        """Builds a complete set of permissions based on defaults with values
        updated by task parameters.

        :return: A complete set of permissions.
        parameters.
        :rtype: dict
        """
        default_permissions = dict(permissions=_default_perms)
        built_permissions = copy.deepcopy(default_permissions)
        for key in default_permissions["permissions"]:
            if self.module.params["permissions"] is None:
                built_permissions = default_permissions
            else:
                if self.module.params["permissions"][key] is not None:
                    for key_2, value_2 in self.module.params["permissions"][
                        key
                    ].items():
                        built_permissions["permissions"][key][key_2] = value_2
        return built_permissions

    def build_ip_whitelist(self):
        """Builds a list of dicts modeled to be the same as the API call.

        :return: A list of dicts
        :rtype: list
        """
        built_ip_whitelist = dict(ip_whitelist=[])
        if self.module.params["ip_whitelist"] is not None:
            built_ip_whitelist["ip_whitelist"] = self.module.params["ip_whitelist"]
        return built_ip_whitelist

    def build_changes(self):
        """Builds a complete API call by assembling returned data from functions.

        :return: A complete API call.
        parameters.
        :rtype: dict
        """
        built_changes = dict(
            name=self.module.params.get("name"),
        )
        built_changes.update(self.build_permissions())
        built_changes.update(self.build_ip_whitelist())
        return built_changes

    def present(self, before, team_id):
        """Goes through the process of creating a new team, if needed, or
        updating a pre-existing one with new permissions.

        :param team_id: Previously collected id if the team exists.
        :type team_id: str
        :return: Tuple in which first value reflects whether or not a change
        occurred and second value is new or updated team object
        :rtype: tuple(bool, dict)
        """
        changed = False
        team = None
        built_changes = self.build_changes()
        if self.module.check_mode:
            team = built_changes
        else:
            if team_id is None:
                team = self.create(built_changes)
            else:
                team = self.update(team_id, built_changes)
        if team != before:
            changed = True
        return changed, team

    def absent(self, team_id):
        """Deletes an existing team or reports back no change if the team
        does not exist to start with.

        :param team_id: Previously collected id if the team exists.
        :type team_id: str
        :return: Tuple in which first value reflects whether or not a change
        occurred and second value is the removed team object
        :rtype: tuple(bool, dict)
        """
        if team_id is None:
            return False
        else:
            self.delete(team_id)
            return True

    def get_team_id(self, before):
        """Takes gathered information of a pre-existing team and looks for the
        id required by update and delete actions.

        :param before: Existing team info
        :type before: dict
        :return: Id of an existing team
        :rtype: str
        """
        if before is not None:
            team_id = before["id"]
            return team_id

    def check_existence(self, team_name):
        """Does a call to see if the team given in ansible task params already
        exists to establish existing state before changes are made. Also, this
        is the first step in getting team_id for later changes.

        :param team_name: Existing set of parameters
        :type have: str
        :return: Team info before changes. If no info found then None will be returned.
        :rtype: dict
        """
        team_list = self.ns1.team()
        for team in team_list.list():
            if team["name"].lower() == team_name.lower():
                team_found = team
                return team_found

    def exec_module(self):
        """Main execution method of module.  Creates, updates or deletes a
        team based on Ansible parameters.

        :return: Results of module execution
        :rtype: dict
        """
        # Setup and gather info
        ## Retreive the name passed into the module from a task.
        team_name = self.module.params.get("name")
        ## Creates a var that will contain data of an existing team or be a None Type.
        ## The None type is used for determining state.
        before = self.check_existence(team_name)
        ## Passes in the `before` var for type comparision and returning required data for later calls if a team already exists.
        team_id = self.get_team_id(before)
        # Take action based on module params with gathered info passed in.
        ## Retreive desired state passed into the module from a task.
        state = self.module.params.get("state")
        ## Action based on a team state being set to present.
        ## Will result in a team being created or updated.
        if state == "present":
            changed, team = self.present(before, team_id)
        ## Action based on a team state being set to absent.
        ## Assumes a team to remove already exists.
        if state == "absent":
            changed = self.absent(team_id)
            team = {}
        # Takes passed in state changes for id scrubbing and building of final output.
        return self.build_result(changed, team, before, team_name)

    def build_result(self, changed, team, before, team_name):
        """Builds dict of results from module execution to pass to module.exit_json()

        :param changed: Whether or not a change occurred
        :type changed: bool
        :param zone: Zone object returned by NS1 of new or updated zone
        :type zone: dict
        :return: Results of module execution
        :rtype: dict
        """
        result = {"changed": changed}
        if self.module._diff:
            result.update(diff={"before": {}, "after": {}, "team": team_name})
            if before is not None:
                result["diff"]["before"] = before
            if team is not None:
                result["diff"]["after"] = team
        return self.remove_ids(result)

    def remove_ids(self, result):
        result_2 = copy.deepcopy(result)
        for k, v in result["diff"].items():
            if not isinstance(v, str):
                # ? Is there a better way to do this?
                # ? Is this a good use of try/except?
                if "id" in result_2["diff"][k]:
                    del result_2["diff"][k]["id"]
                try:
                    for entry in result_2["diff"][k]["ip_whitelist"]:
                        del entry["id"]
                except KeyError:
                    pass
        return result_2


def main():
    t = NS1Team()
    result = t.exec_module()
    t.module.exit_json(**result)


if __name__ == "__main__":
    main()
