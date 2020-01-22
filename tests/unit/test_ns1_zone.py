import pytest
import ns1.zones
from .common import FakeAnsibleModule, AnsibleExitJson, AnsibleFailJson
from library import ns1_zone
from unittest.mock import patch


@pytest.mark.usefixtures("mock_module_helper")
def test_module_fail_when_required_args_missing():
    with pytest.raises(AnsibleFailJson):
        FakeAnsibleModule.set_module_args({})
        ns1_zone.main()


@pytest.mark.parametrize(
    "have,want,exp",
    [
        pytest.param({}, {"nx_ttl": 1}, {"nx_ttl": 1}, id="missing_param"),
        pytest.param(
            {},
            {"networks": [1, 2, 3]},
            {"networks": [1, 2, 3]},
            id="missing_set_param",
        ),
        pytest.param(
            {},
            {"secondary": {"enabled": True}},
            {"secondary": {"enabled": True}},
            id="missing_dict_param",
        ),
        pytest.param(
            {"nx_ttl": 0},
            {"nx_ttl": 1},
            {"nx_ttl": 1},
            id="updated_param"),
        pytest.param(
            {"networks": [1, 2, 3]},
            {"networks": [3, 4, 5]},
            {"networks": [3, 4, 5]},
            id="updated_set_param",
        ),
        pytest.param(
            {"secondary": {"enabled": True}},
            {"secondary": {"enabled": True, "primary_port": 0}},
            {"secondary": {"primary_port": 0}},
            id="updated_dict_param",
        ),
        pytest.param(
            {"networks": [1, 2, 3]},
            {"networks": []},
            {"networks": []},
            id="removed_set_param",
        ),
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 0}, {}, id="no_diff_param"),
        pytest.param(
            {"networks": [1, 2, 3]},
            {"networks": [3, 2, 1]},
            {},
            id="ignore_set_param_order",
        ),
        pytest.param(
            {"secondary": {"enabled": True}},
            {"secondary": {"enabled": True}},
            {},
            id="no_diff_dict_param",
        ),
    ],
)
@pytest.mark.usefixtures("mock_module_helper")
def test_compare_params(have, want, exp):
    zone = "test.zone"
    FakeAnsibleModule.set_module_args({"apiKey": "testkey", "name": zone})
    z = ns1_zone.NS1Zone()
    assert z.compare_params(have, want) == exp


@pytest.mark.parametrize(
    "zone_data,module_args,exp_changed,exp_update",
    [
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 0}, False, {}, id="no_change"),
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 1}, True, {"nx_ttl": 1}, id="change_param"),
        pytest.param({"networks": [1,2]}, {"networks": [2,1]}, False, {}, id="no_change_set"),
        pytest.param({"networks": [1]}, {"networks": [1,2]}, True, {"networks": [1,2]}, id="change_set"),
        pytest.param(
            {"secondary": {"enabled": True}},
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            True,
            {"secondary": {"primary_ip": "1.1.1.1"}},
            id="change_suboption"
        ),
    ]
)
@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.zones.Zone.update")
def test_update(mock_zone_update, ns1_config, zone_data, module_args, exp_changed, exp_update):
    m = FakeAnsibleModule("test.zone")

    mock_zone = ns1.zones.Zone(ns1_config, m.name)
    mock_zone.data = m.get_zone_data(**zone_data)

    exp_exit_json = "'changed': {}".format(exp_changed)
    with pytest.raises(AnsibleExitJson, match=exp_exit_json):
        FakeAnsibleModule.set_module_args(m.get_args(**module_args))
        z = ns1_zone.NS1Zone()
        z.update(mock_zone)
    if exp_changed:
        mock_zone_update.assert_called_once_with(**m.get_request_args(**exp_update))
    else:
        assert not mock_zone_update.called


@pytest.mark.parametrize(
    "module_args,exp_params",
    [
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 0}, id="single_param"),
        pytest.param(
            {"nx_ttl": 0, "ttl": None},
            {"nx_ttl": 0},
            id="none_param",
        ),
        pytest.param(
            {"nx_ttl": 0, "name": "foo"},
            {"nx_ttl": 0},
            id="ignored_param",
        ),
        pytest.param(
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            id="suboption"
        ),
        pytest.param(
            {"secondary": {"enabled": True, "primary_ip": None}},
            {"secondary": {"enabled": True}},
            id="none_suboption"
        ),
    ]
)
def test_sanitize_params(module_args, exp_params):
    z = ns1_zone.NS1Zone()
    params = z.sanitize_params(module_args)
    assert params == exp_params
