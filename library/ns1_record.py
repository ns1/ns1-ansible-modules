#!/usr/bin/python

# Copyright: (c) 2019, Matthew Burtless <mburtless@ns1.com>
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
---
module: ns1_record

short_description: Create, modify and delete NS1 hosted DNS records.

version_added: "2.9"

description:
  - Create, modify and delete record objects within an existing zone.

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
      - Whether the record should be present or not.  Use C(present) to create
        or update and C(absent) to delete.
    type: str
    default: present
    choices:
      - absent
      - present
  name:
    description:
      - The subdomain of the record. For apex records, this should match the
        value of I(zone).
    type: str
    required: true
  zone:
    description:
      - Name of the existing DNS zone in which to manage the record.
    type: str
    required: true
  answers:
    description:
      - An array of answers for this record (order matters). This can take
        many forms depending on record type and desired effect. See
        U(https://ns1.com/api) for more details.
    type: list
    required: true
    suboptions:
      answer:
        description:
          - An array of RDATA values for this answer
        type: list
        required: false
      meta:
        description:
          - Answer level metadata
        type: dict
        required: false
      region:
        description:
          - Region (Answer Group) that the answer belongs to.
        type: str
        required: false
  ignore_missing_zone:
    description:
      - Attempting to delete a record from a zone that is not present will
        normally result in an error. This error can be ignored by setting this
        flag to C(True). This module will then count any record without a valid
        zone as absent.  This is useful for ensuring a record is absent,
        regardless of the status of its zone.
    type: bool
    required: false
    default: false
  record_mode:
    description:
      - Whether existing I(answers) or I(filters) values unspecified in the
        module should be purged
    type: str
    default: purge
    choices:
      - append
      - purge
  type:
    description:
      - The type of the record to create, modify or delete.
    type: str
    required: true
    choices:
      - A
      - AAAA
      - ALIAS
      - AFSDB
      - CNAME
      - DNAME
      - HINFO
      - MX
      - NAPTR
      - NS
      - PTR
      - RP
      - SPF
      - SRV
      - TXT
  use_client_subnet:
    description:
      - Whether record should be EDNS-Client-Subnet enabled
    type: bool
    required: false
  meta:
    description:
      - Record level metadata.
    type: dict
    required: false
  link:
    description:
      - The target of a linked record.
    type: str
    required: false
  filters:
    description:
      - An array of filters for the record, for use in configuring dynamic
        records (order matters)
    type: list
    required: false
    suboptions:
      filter:
        description:
          - The type of filter.
        type: str
        required: false
      config:
        description:
          - The filters' configuration
        type: dict
        required: false
  ttl:
    description:
      - The TTL of the record.
    type: int
    required: false
    default: 3600
  regions:
    description:
      - The regions object for the record set.
    type: dict
    required: false

extends_documentation_fragment:
  - ns1

author:
  - 'Matthew Burtless (@mburtless)'
'''

EXAMPLES = '''
- name: Ensure an A record with two answers, metadata and filter chain
  ns1_record:
    apiKey: "{{ ns1_token }}"
    name: www
    zone: test.com
    state: present
    type: A
    answers:
        - answer:
            - 192.168.1.0
          meta:
            up: True
        - answer:
            - 192.168.1.1
          meta:
            up: True
    filters:
        - filter: up
          config: {}

- name: Ensure an A record, appending new answer to existing
  ns1_record:
    apiKey: "{{ ns1_token }}"
    name: www
    zone: test.com
    record_mode: append
    state: present
    type: A
    answers:
        - answer:
            - 192.168.1.3
          meta:
            up: True

- name: Delete an A record
  ns1_record:
    apiKey: "{{ ns1_token }}"
    name: www
    zone: test.com
    state: absent
    type: A
    answers: []

- name: Ensure an MX record at apex of zone with a single answer
  ns1_record:
    apiKey: "{{ ns1_token }}"
    name: test.com
    zone: test.com
    state: present
    type: MX
    answers:
      - answer:
          - 5
          - mail1.example.com

- name: Register list of datasources
  ns1_datasource_info
    apiKey: "{{ ns1_token }}"
  register: datasource_info
- name: An answer with a connected data feed
  ns1_record:
    apiKey: "{{ ns1_token }}"
    name: test.com
    zone: test.com
    state: present
    type: A
    answers:
        - answer:
            - 192.168.1.3
          meta:
            up:
              feed: {{ datasource_info.datasources.datadog.feeds[0].id }}
'''

RETURN = '''
'''

import copy  # noqa
import ruamel.yaml as yaml

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

RECORD_KEYS_MAP = dict(
    use_client_subnet=dict(appendable=False),
    answers=dict(appendable=True),
    meta=dict(appendable=False),
    link=dict(appendable=False),
    filters=dict(appendable=True),
    ttl=dict(appendable=False),
    regions=dict(appendable=False),
)

RECORD_TYPES = [
    'A',
    'AAAA',
    'ALIAS',
    'AFSDB',
    'CNAME',
    'DNAME',
    'HINFO',
    'MX',
    'NAPTR',
    'NS',
    'PTR',
    'RP',
    'SPF',
    'SRV',
    'TXT',
]


class NS1Record(NS1ModuleBase):
    def __init__(self):
        self.module_arg_spec = dict(
            name=dict(required=True, type='str'),
            zone=dict(required=True, type='str'),
            answers=dict(
                required=True,
                type='list',
                elements='dict',
                options=dict(
                    answer=dict(type='list', default=None),
                    meta=dict(type='dict', default=None),
                    region=dict(type='str', default=None),
                ),
            ),
            ignore_missing_zone=dict(
                required=False, type='bool', default=False
            ),
            type=dict(required=True, type='str', choices=RECORD_TYPES),
            use_client_subnet=dict(required=False, type='bool', default=None),
            meta=dict(required=False, type='dict', default=None),
            link=dict(required=False, type='str', default=None),
            filters=dict(
                required=False,
                type='list',
                elements='dict',
                default=None,
                options=dict(
                    filter=dict(type='str', default=None),
                    config=dict(type='dict', default=None),
                ),
            ),
            ttl=dict(required=False, type='int', default=3600),
            regions=dict(required=False, type='dict', default=None),
            state=dict(
                required=False,
                type='str',
                default='present',
                choices=['present', 'absent'],
            ),
            record_mode=dict(required=False,
                             type='str',
                             default='purge',
                             choices=['append', 'purge']),
        )

        NS1ModuleBase.__init__(self,
                               self.module_arg_spec,
                               supports_check_mode=True)

    def filter_empty_subparams(self, param_name):
        """Used to remove any possible empty module params passed in from a
           task file.

        :param param_name: Name of the parameter being passed into the module.
                           Ie zone.
        :type param_name: Any
        :return: Paramaters that are not empty.
        :rtype: list
        """
        param = self.module.params.get(param_name)
        filtered = []
        if isinstance(param, list):
            for subparam in param:
                if isinstance(subparam, dict):
                    filtered.append(
                        dict(
                            (key, value)
                            for key, value in subparam.items()
                            if value is not None
                        )
                    )
        else:
            filtered = param
        return filtered

    def api_params(self):
        """Sets up other paramters for the api call that may not be specified
           in the modules from tasks file.

        :return: Default params if they are not specified in the module but
                 required by the API.
        :rtype: dict
        """
        params = dict(
            (key, self.module.params.get(key))
            for key, value in RECORD_KEYS_MAP.items()
            if key != "answers" and self.module.params.get(key) is not None
        )
        return params

    def sanitize_record(self, record):
        """Remove fields from the API-returned record that we don't want to
        pass back, or consider when diffing.

        :param record: JSON record information from the API.
        :type record: Any
        :return: Record sans ID info.
        :rtype: list | dict | any
        """
        def remove_ids(d):
            if isinstance(d, dict):
                if 'id' in d:
                    del d['id']
                for key, val in d.items():
                    if isinstance(val, (dict, list)):
                        remove_ids(val)
            if isinstance(d, list):
                for i in d:
                    if isinstance(i, (dict, list)):
                        remove_ids(i)
            return d

        record = remove_ids(record)
        for answer in record['answers']:
            answer.pop('feeds', None)
        return record

    def get_zone(self):
        """Used to get the zone associated with the record being worked on.

        :return: returns the zone specified in module param in playbook/role.
        :rtype: str
        """
        to_return = None
        try:
            to_return = self.ns1.loadZone(self.module.params.get('zone'))
        except ResourceException as re:
            if re.response.code == 404:
                if (
                    self.module.params.get('ignore_missing_zone')
                    and self.module.params.get('state') == "absent"
                ):
                    # zone not found but we are in the absent state
                    # and the user doesn't care that the zone doesn't exist
                    # nothing to do and no change
                    self.module.exit_json(changed=False)
            else:
                # generic error or user cares about missing zone
                self.module.fail_json(
                    msg="error code %s - %s " % (re.response.code, re.message)
                )
        return to_return

    def get_record(self, zone):
        """Used to look up the record name and type from the specified zone.

        :param zone: Zone name, like 'example.com'.
        :type zone: str
        :return: ends back two str. One for domain and one for type.
        :rtype: str
        """
        to_return = None
        try:
            to_return = zone.loadRecord(self.module.params.get('name'),
                                        self.module.params.get('type').upper())
        except ResourceException as re:
            if re.response.code != 404:
                self.module.fail_json(
                    msg="error code %s - %s " % (re.response.code, re.message)
                )
                to_return = None
        return to_return

    def update(self, record):
        """Used to handle records with values changing.

        :param record: JSON record information from the API. 
        :type record: Obj
        """
        # clean copy of record to preserve IDs for response if no update required
        record_data = self.sanitize_record(copy.deepcopy(record.data))
        changed = False
        args = {}

        for key in RECORD_KEYS_MAP:
            input_data = self.filter_empty_subparams(key)

            if input_data is not None:
                if (
                    RECORD_KEYS_MAP[key]['appendable']
                    and self.module.params.get('record_mode') == 'append'
                ):
                    # create union of input and existing record data,
                    # preserving existing order
                    input_data = record_data[key] + [
                        input_obj
                        for input_obj in input_data
                        if input_obj not in record_data[key]
                    ]

                if input_data != record_data[key]:
                    changed = True
                    args[key] = input_data

        # create a new copy of the previously sanitized dict that will be updated with chaning args to support --diff
        after_changes = copy.deepcopy(record_data)
        for k, v in args.items():
            if after_changes[k] != v:
              after_changes[k] = v

        # check mode short circuit before update
        if self.module.check_mode:
            self.record_exit(before=record_data,
                             changed=changed,
                             after=after_changes,
                             record=record)

        # update only if some changed data
        if changed:
            record.update(errback=self.errback_generator(),
                          **args)

            self.record_exit(before=record_data,
                             changed=changed,
                             after=after_changes,
                             record=record)

        # catch exit if not running in check mode and no changes are to be made.
        self.record_exit(changed=False, record=record)

    def record_exit(self, after=None, before=None, changed=None, record=None):
        """Central exit point for the module.

        :param record: Info about the record being worked with in a before
                       change state.
        :type : str
        :param zone: Info about the zone a record belongs to.
        :type : str
        :param changed: Tell ansible if there has been a change made and to
                        mark the task accordingly.
        :type : Bool
        """
        # convert dictionaries to yaml txt dump
        before_yaml = yaml.safe_dump(before, default_flow_style=False)
        after_yaml = yaml.safe_dump(after, default_flow_style=False)

        # build the final dict to pass into exit_json
        if self.module._diff:
            exec_result = dict(
                diff={'before': {}, 'after': {}})
            if after is not None:
                exec_result['diff']['after'] = after_yaml
            if before is not None:
                exec_result['diff']['before'] = before_yaml
            if changed is not None:
                exec_result['changed'] = changed
            if record is not None:
                try:
                    exec_result['record'] = record.data
                except AttributeError:
                    exec_result['record'] = record
            self.module.exit_json(**exec_result)

        # catch if the module is not being run with --diff
        self.module.exit_json(changed=changed)

    def exec_module(self):
        """Method called by main to handle record state logic handling.
        """
        state = self.module.params.get('state')
        zone = self.get_zone()
        if zone is None:
            self.module.fail_json(msg='zone "{}" not found'.format(
                self.module.params.get('zone')
            ))
        record = self.get_record(zone)

        # record found
        if record:
            # absent param handling
            if state == "absent":
                if self.module.check_mode:
                    # short circut in check mode
                    # self.module.exit_json(changed=True)
                    self.record_exit(before=record.data,
                                     changed=True, record=record)
                record.delete(errback=self.errback_generator())
                self.record_exit(before=record.data,
                                 changed=True, record=record)
            # present param handling - Create and update go down the same
            # path when record is found.
            else:
                self.update(record)

        # record not found
        else:
            # absent param handling
            if state == "absent":
                self.module.exit_json(changed=False)
            # present param handling - Create tasks go down this path.
            else:
                # short circuit in check mode
                if self.module.check_mode:
                    # setting record to module params as nothing has been
                    # returned from the API to use for --diff
                    record = self.module.params
                    self.record_exit(changed=True, after=record, record=record)

                method_to_call = getattr(
                    zone, 'add_%s' % (self.module.params.get('type').upper())
                )
                record = method_to_call(
                    self.module.params.get('name'),
                    self.filter_empty_subparams('answers'),
                    errback=self.errback_generator(),
                    **self.api_params()
                )
                self.record_exit(
                    changed=True, after=record.data, record=record)


def main():
    r = NS1Record()
    r.exec_module()


if __name__ == '__main__':
    main()
