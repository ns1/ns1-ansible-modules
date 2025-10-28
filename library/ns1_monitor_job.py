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
module: ns1_monitor_job

short_description: Create, modify, and delete NS1 monitoring jobs.

version_added: "2.9"

description:
  - Manages health check jobs within NS1, allowing configuration of URLs,
    ports, expected status codes, and monitoring regions.

options:
  name:
    description:
      - The human-readable name for the monitoring job. (Maps to JSON 'name')
    type: str
    required: true
  job_type:
    description:
      - The type of monitoring job (e.g., http, ping, tcp). (Maps to JSON 'job_type')
    type: str
    required: true
    choices:
      - http
      - ping
      - tcp
  active:
    description:
      - Whether the monitoring job should be C(true) (enabled) or C(false) (disabled) upon creation/update.
    type: bool
    required: false
    default: true
  mute:
    description:
      - Whether to suppress notifications for the monitoring job. Set to C(true) to mute notifications.
    type: bool
    required: false
    default: false
  frequency:
    description:
      - The frequency (in seconds) at which to run the monitor job.
    type: int
    default: 60
  policy:
    description:
      - The monitoring policy (e.g., quorum, all, or comma-separated regions).
    type: str
    default: quorum
  notify_delay:
    description:
      - Time (in seconds) to wait after a failure before sending a notification.
    type: int
    required: false
    default: 0
  notify_repeat:
    description:
      - Time (in seconds) between repeat notifications while the job remains in a failed state.
    type: int
    required: false
    default: 0
  notify_failback:
    description:
      - Whether to send a notification when the job returns to an 'up' state.
    type: bool
    required: false
    default: true
  notify_regional:
    description:
      - Whether to send notifications for regional failures, in addition to global status changes.
    type: bool
    required: false
    default: false
  notify_list:
    description:
      - The unique ID of the notification list to send alerts to. Must be a single string ID.
    type: str
    required: false
  rapid_recheck:
    description:
      - Whether the job should be quickly re-run (after a 1 second delay) upon a state change before sending a notification.
    type: bool
    required: false
    default: false
  notes:
    description:
      - Free-form text notes to attach to the monitoring job.
    type: str
    required: false
  regions:
    description:
      - List of NS1 regions to run the job from (e.g., ['lhr', 'sin']). (Maps to JSON 'regions')
    type: list
    required: false
config:
    description:
      - Dictionary containing job-specific configuration parameters. These settings vary based on the I(job_type).
    type: dict
    required: true
    suboptions:
      url:
        description:
          - The full URL (including scheme and port) that the monitor job will check.
        type: str
        required: true
      connect_timeout:
        description:
          - The amount of time (in seconds) to wait when establishing a connection.
        type: int
        required: false
      idle_timeout:
        description:
          - The amount of time (in seconds) to wait for a response after connection is established.
        type: int
        required: false
      tls_add_verify:
        description:
          - Whether to enforce TLS certificate verification. Set to C(false) to bypass certificate errors.
        type: bool
        required: false
      follow_redirect:
        description:
          - Whether to follow HTTP redirects (3xx status codes).
        type: bool
        required: false
      user_agent:
        description:
          - The value of the User-Agent header to send with the request.
        type: str
        required: false
      ipv6:
        description:
          - Whether to force monitoring over IPv6.
        type: bool
        required: false
rules:
    description:
      - Array of rules defining successful outcomes that the monitor job must satisfy to be marked 'Up'.
    type: list
    required: true
    elements: dict
    suboptions:
      comparison:
        description:
          - The comparison operator to use.
        type: str
        required: true
        choices:
          - '=='
          - '!='
          - '>'
          - '>='
          - '<'
          - '<='
          - '=~'
          - '!~'
      key:
        description:
          - The key of the job output metric to compare (e.g., 'status_code' for HTTP checks).
        type: str
        required: true
      value:
        description:
          - The value to compare against the output key (e.g., '200'). Must be a string.
        type: str
        required: true
  apiKey:
    description:
      - Unique client api key.
    type: str
    required: true
  state:
    description:
      - Whether the job should be C(present) or C(absent). Use C(present) to create
        or update and C(absent) to delete.
    type: str
    default: present
    choices:
      - absent
      - present

extends_documentation_fragment:
  - ns1

author:
  - 'Michael Kearey'
'''

EXAMPLES = '''
- name: Ensure HTTPS monitor is present
  ns1_monitor_job:
    apiKey: "{{ ns1_token }}"
    name: rhcoresite.vpn.neuralmagic.com-943
    state: present
    job_type: http
    frequency: 30
    policy: quorum
    config:
      url: https://rhcoresite.vpn.neuralmagic.com:943/
      connect_timeout: 5
      idle_timeout: 3
    rules:
      - comparison: '=='
        key: 'status_code'
        value: '200'

- name: Delete a monitoring job
  ns1_monitor_job:
    apiKey: "{{ ns1_token }}"
    name: rhcoresite.vpn.neuralmagic.com-943
    state: absent
    job_type: http
'''

RETURN = '''
# Returns the full JSON representation of the monitor job on success.
'''

import copy  # noqa
import ruamel.yaml as yaml
import json # Import json for string/type handling

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

# Define the keys that can be updated in the monitor job
MONITOR_KEYS_MAP = dict(
    active=dict(appendable=False),
    mute=dict(appendable=False),
    frequency=dict(appendable=False),
    policy=dict(appendable=False),

    notify_delay=dict(appendable=False),
    notify_repeat=dict(appendable=False),
    notify_failback=dict(appendable=False),
    notify_regional=dict(appendable=False),
    notify_list=dict(appendable=False),
    rapid_recheck=dict(appendable=False),
    notes=dict(appendable=False),

    regions=dict(appendable=False),
    config=dict(appendable=False),
    rules=dict(appendable=False),
)

class NS1MonitorJob(NS1ModuleBase):
    def __init__(self):
        self.module_arg_spec = dict(
            apiKey=dict(required=True, type='str'),
            state=dict(required=False, type='str', default='present', choices=['present', 'absent']),
            
            name=dict(required=True, type='str'),
            job_type=dict(required=True, type='str', choices=['http', 'ping', 'tcp']),
            
            frequency=dict(required=False, type='int', default=60),
            policy=dict(required=False, type='str', default='quorum'),
            active=dict(required=False, type='bool', default=None),
            mute=dict(required=False, type='bool', default=None),
            rapid_recheck=dict(required=False, type='bool', default=None),
            
            notify_failback=dict(required=False, type='bool', default=None),
            notify_regional=dict(required=False, type='bool', default=None),
            notify_delay=dict(required=False, type='int', default=0),
            notify_repeat=dict(required=False, type='int', default=0),
            notify_list=dict(required=False, type='str', default=None),
            notes=dict(required=False, type='str', default=None),
            
            regions=dict(required=False, type='list', default=None),
            config=dict(required=True, type='dict'),
            rules=dict(required=True, type='list', elements='dict'),
        )
        NS1ModuleBase.__init__(self, self.module_arg_spec, supports_check_mode=True)

    def api_params(self):
        """Sets up other parameters for the api call that may not be specified
        in the modules from tasks file.
        """
        params = dict(
            (key, self.module.params.get(key))
            for key in MONITOR_KEYS_MAP
            if self.module.params.get(key) is not None
        )
        
        # Ensure 'regions' and 'rules' is an empty list if None
        if self.module.params.get('regions') is None:
            params['regions'] = []
        if self.module.params.get('rules') is None:
            params['rules'] = []
        #Ensure if notifyList is an empty string that its not passed on    
        if self.module.params.get('notify_list') == '':
             params.pop('notify_list', None)

        return params

    def sanitize_job(self, job):
        """Remove API-generated fields and normalize types for diffing, ordered by API response keys."""
        job.pop('id', None)
        job.pop('name', None)
        job.pop('status', None)
        job.pop('created_at', None)
        job.pop('updated_at', None)
        job.pop('last_run', None)
        job.pop('region_scope', None)
        
        if 'config' in job and job['config'] is not None:
            job['config'].pop('follow_redirect', None)
            job['config'].pop('ipv6', None)
            job['config'].pop('user_agent', None)
            job['config'].pop('response_codes', None) 
            
        if 'regions' in job and job['regions'] is not None:
             job['regions'] = sorted(job['regions'])

        return job

    def get_job(self):
        """Loads an existing job by name and returns the SDK object."""
        try:
            # We list all jobs to find the ID since we only have the name.
            jobs = self.ns1.monitors().list()
            for job_data in jobs:
                if job_data.get('name') == self.module.params.get('name'):
                    # Load the job object using its ID
                    return self.ns1.monitors().retrieve(job_data.get('id'))
            return None # Job not found
            
        except ResourceException as re:
            self.module.fail_json(msg="Error retrieving monitor list: %s" % re.message)

    def create_job(self):
        """Handles creating a new monitoring job."""
        
        name = self.module.params.get('name')
        job_type = self.module.params.get('job_type')
        active = self.module.params.get('active')
        mute = self.module.params.get('mute')
        frequency = self.module.params.get('frequency')
        policy = self.module.params.get('policy')
        
        config = self.module.params.get('config')
        rules = self.module.params.get('rules')
        
        args = self.api_params()

        body = {
            'name': name,
            'job_type': job_type,
            'active': active,
            'mute': mute,
            'frequency': frequency,
            'policy': policy,
            
            'config': config,
            'rules': rules,
        }

        body.update(args)
        body = {k: v for k, v in body.items() if v is not None}
        
        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Monitor job would be created.")

        try:
            job = self.ns1.monitors().create(body, errback=self.errback_generator())
        except Exception as e:
            self.module.fail_json(msg="NS1 API job creation failed: %s" % str(e))

        if hasattr(job, 'data'):
            return job.data
        else:
            return job

    def update_job(self, job_obj):
        """Handles updating an existing job."""
        import q 
        current_data = self.sanitize_job(copy.deepcopy(job_obj))
        changed = False
        full_input_args = {}

        
        for key in MONITOR_KEYS_MAP:
            input_data = self.module.params.get(key)
            
            if input_data is None:
                continue

            modified_input = copy.deepcopy(input_data)
            
            # --- Input Normalization ---
            if key == 'regions' and isinstance(modified_input, list):
                modified_input = sorted(modified_input)
            
            if key == 'config':
                if 'idle_timeout' in modified_input:
                    modified_input['idle_timeout'] = int(modified_input['idle_timeout'])
                if 'connect_timeout' in modified_input:
                    modified_input['connect_timeout'] = int(modified_input['connect_timeout'])

                if modified_input.get('follow_redirect') is False:
                    modified_input.pop('follow_redirect', None)
                if modified_input.get('ipv6') is False:
                    modified_input.pop('ipv6', None)
                if modified_input.get('user_agent') == 'NS1 HTTP Monitoring Job':
                    modified_input.pop('user_agent', None)
            
            full_input_args[key] = modified_input

            if key in current_data:
                if modified_input != current_data[key]:
                    q(modified_input)
                    q(current_data[key])
                    changed = True
            elif key not in current_data:
                changed = True

        if not changed:
            self.module.exit_json(changed=False, job=job_obj)

        if self.module.check_mode:
            self.module.exit_json(changed=True, msg="Monitor job would be updated.")

        update_payload = copy.deepcopy(job_obj)
        update_payload.update(full_input_args)
        
        update_payload['name'] = self.module.params.get('name')
        update_payload['job_type'] = self.module.params.get('job_type')

        job_id = job_obj.get('id')
        
        try:
            # Call the REST client update method: Monitors.update(jobid, body, ...)
            job = self.ns1.monitors().update(
                job_id,                             # Positional Arg 1: jobid (URL path)
                update_payload,                     # Positional Arg 2: body (full payload dict)
                errback=self.errback_generator()
            )
        except Exception as e:
            self.module.fail_json(
                msg="Failed to update monitor job via API: %s" % str(e),
                payload=update_payload
            )

        return job

    def exec_module(self):
        """Entry point for the module."""
        state = self.module.params.get('state')
        job_obj = self.get_job() # Job is the SDK object OR None

        if state == "absent":
            if job_obj:
                if self.module.check_mode:
                    self.module.exit_json(changed=True, msg="Monitor job would be deleted.")
                
                job_id = job_obj.get('id')
                self.ns1.monitors().delete(job_id, errback=self.errback_generator())
                self.module.exit_json(changed=True, msg="Monitor job deleted.")
            else:
                self.module.exit_json(changed=False, msg="Monitor job already absent.")

        # state == "present"
        if job_obj:
            # Job found, update it
            try:
                job_data = self.update_job(job_obj)
                #job_data.pop('errback', None)
                self.module.exit_json(changed=True, job=job_data)
            except Exception as e:
                self.module.fail_json(msg="Failed to update monitor job: %s" % str(e))
        else:
            # Job not found, create it
            try:
                job_data = self.create_job()
                #job_data.pop('errback', None)
                self.module.exit_json(changed=True, job=job_data)
            except Exception as e:
                self.module.fail_json(msg="Failed to create monitor job: %s" % str(e))


def main():
    job_module = NS1MonitorJob()
    job_module.exec_module()


if __name__ == '__main__':
    main()
