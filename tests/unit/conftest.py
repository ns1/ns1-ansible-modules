import pytest
from ns1 import Config
from ansible.module_utils import basic
from .common import FakeAnsibleModule

try:  # Python 3.3 +
    from unittest.mock import patch
except ImportError:
    from mock import patch


@pytest.fixture
def zones_update_helper(request):
    """Patches ns1.zones.Zone.Update function

    :param request: requesting test context
    :type request: FixtureRequest
    """
    zones_update_helper = patch("ns1.zones.Zone.update")
    zones_update_helper.start()
    request.addfinalizer(zones_update_helper.stop)


@pytest.fixture
def ns1_config():
    """Returns a mock NS1 SDK config object

    :return: Mock NS1 SDK config object
    :rtype: Config
    """
    c = Config()
    c.loadFromDict(
        {
            "endpoint": "api.nsone.net",
            "default_key": "test1",
            "keys": {
                "test1": {
                    "key": "key-1",
                    "desc": "test key number 1",
                    "writeLock": True,
                }
            },
        }
    )
    return c


@pytest.fixture()
def mock_module_helper(request):
    """Patches Ansible module exit_json, fail_json and get_bin_path methods

    :param request: requesting test context
    :type request: FixtureRequest
    """
    mock_module_helper = patch.multiple(
        basic.AnsibleModule,
        exit_json=FakeAnsibleModule.exit_json,
        fail_json=FakeAnsibleModule.fail_json,
        get_bin_path=FakeAnsibleModule.get_bin_path,
    )
    mock_module_helper.start()
    request.addfinalizer(mock_module_helper.stop)
