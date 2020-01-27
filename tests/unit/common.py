from ansible.module_utils._text import to_bytes
from ansible.module_utils import basic
import json

try:  # Python 3.3 +
    from unittest.mock import ANY
except ImportError:
    from mock import ANY


class FakeAnsibleModule:
    """Collection of methods for working with patched Ansible module
    """

    def __init__(self, name):
        """Constructor method
        """
        self.name = name

    @staticmethod
    def set_module_args(args):
        """prepare arguments so that they will be picked up during module creation

        :param args: args for Ansible to use during module creations
        :type args: list
        """
        args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
        basic._ANSIBLE_ARGS = to_bytes(args)

    @staticmethod
    def exit_json(*args, **kwargs):
        """function to patch over exit_json; package return data into an exception.
        If changed not provided as kwarg, defaults to False.

        :param args: args for Ansible to use during module exit
        :type args: list
        :param kwargs: args for Ansible to use during module exit
        :type kwargs: dict
        :raises AnsibleExitJson: Ansible exit with kwargs returned as json
        """
        if "changed" not in kwargs:
            kwargs["changed"] = False
        raise AnsibleExitJson(kwargs)

    @staticmethod
    def fail_json(*args, **kwargs):
        """Function to patch over fail_json; package return data into an exception

        :param args: args for Ansible to use during module fail
        :type args: list
        :param kwargs: args for Ansible to use during module fail
        :type kwargs: dict
        :raises AnsibleFailJson: Ansible failure with kwargs returned as json
        """
        kwargs["failed"] = True
        raise AnsibleFailJson(kwargs)

    def get_bin_path(self, arg, required=False):
        """Mock AnsibleModule.get_bin_path function

        :return: Module bin path
        :rtype: str
        """
        if arg.endswith("my_command"):
            return "/usr/bin/my_command"
        else:
            if required:
                self.fail_json(msg="%r not found !" % arg)

    def get_zone_data(self, **kwargs):
        """Returns mock zone data, containing zone name and values and keys from kwargs

        :param kwargs: args to populate mock zone data
        :type kwargs: dict
        :return: Dict of zone params
        :rtype: dict
        """
        data = {"zone": self.name}
        data.update(**kwargs)
        return data

    def get_args(self, **kwargs):
        """Returns mock module args, including zone name, apikey and values
        and keys from kwargs

        :param kwargs: args to populate mock module args
        :type kwargs: dict
        :return: Mock module args
        :rtype: dict
        """
        args = {"name": self.name, "apiKey": "testkey"}
        args.update(**kwargs)
        return args

    def get_request_args(self, **kwargs):
        """Returns a dict of mock SDK request paramaters, including mock
        errback function and keys and values from kwargs.

        :param kwargs: args to populate mock SDK request parameters
        :type kwargs: dict
        :return: Mock SDK request parameters
        :rtype: dict
        """
        args = {"errback": ANY}
        args.update(**kwargs)
        return args


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the
    test case.
    """

    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the
    test case.
    """

    pass
