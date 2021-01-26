import pytest
import ns1.zones

from .common import FakeAnsibleModule, AnsibleFailJson
from library import ns1_zone

try:  # Python 3.3 +
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock


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
            {"nx_ttl": 0}, {"nx_ttl": 1}, {"nx_ttl": 1}, id="updated_param"
        ),
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
            {"secondary": {"enabled": True, "tsig": {"enabled": True}}},
            {
                "secondary": {
                    "enabled": True,
                    "tsig": {"enabled": True, "name": "foo"},
                }
            },
            {"secondary": {"tsig": {"name": "foo"}}},
            id="updated_nested_dict_param",
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
def test_diff_params(have, want, exp):
    FakeAnsibleModule.set_module_args(
        {"apiKey": "testkey", "name": "test.zone"}
    )
    z = ns1_zone.NS1Zone()
    assert z.diff_params(have, want) == exp


@patch("library.ns1_zone.NS1Zone.diff_params")
@patch("library.ns1_zone.NS1Zone.diff_in_secondaries")
def test_get_changed_params(mock_diff_in_secondaries, mock_diff_params):
    z = ns1_zone.NS1Zone()

    # verify we perform compare on secondaries when diff contains secondaries
    # and secondaries is stripped if no diff
    mock_diff_params.return_value = {
        "primary": {"secondaries": [{"ip": "1.1.1.1"}]}
    }
    have = {"primary": {"secondaries": [{"ip": "1.1.1.1"}]}}
    want = {"primary": {"secondaries": [{"ip": "1.1.1.1"}]}}
    mock_diff_in_secondaries.return_value = False
    diff = z.get_changed_params(have, want)
    mock_diff_in_secondaries.assert_called_once()
    assert diff == ({}, {})


@pytest.mark.parametrize(
    "have,want,exp",
    [
        pytest.param(
            [
                {"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True},
                {"ip": "2.2.2.2", "port": 2, "networks": [0], "notify": True},
            ],
            [
                {"ip": "2.2.2.2", "port": 2, "networks": [0], "notify": True},
                {"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True},
            ],
            False,
            id="ignore_secondary_order",
        ),
        pytest.param(
            [
                {
                    "ip": "1.1.1.1",
                    "port": 1,
                    "networks": [0, 1],
                    "notify": True,
                },
            ],
            [
                {
                    "ip": "1.1.1.1",
                    "port": 1,
                    "networks": [1, 0],
                    "notify": True,
                },
            ],
            False,
            id="ignore_networks_order",
        ),
        pytest.param(
            [{"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True}],
            [{"ip": "1.1.1.1", "port": 1, "notify": True}],
            False,
            id="ignore_extra_key_in_have",
        ),
        pytest.param(
            [
                {"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True},
                {"ip": "2.2.2.2", "port": 2, "networks": [0], "notify": True},
            ],
            [{"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True}],
            True,
            id="removed_secondary",
        ),
        pytest.param(
            [{"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True}],
            [
                {"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True},
                {"ip": "2.2.2.2", "port": 2, "networks": [0], "notify": True},
            ],
            True,
            id="added_secondary",
        ),
        pytest.param(
            [{"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True}],
            [{"ip": "1.1.1.1", "port": 2, "networks": [0], "notify": True}],
            True,
            id="updated_param",
        ),
    ],
)
def test_diff_in_secondaries(have, want, exp):
    z = ns1_zone.NS1Zone()
    assert z.diff_in_secondaries(have, want) == exp


def test_convert_secondaries_to_dict():
    z = ns1_zone.NS1Zone()
    secondaries = [
        {"ip": "1.1.1.1", "port": 1, "networks": [0], "notify": True},
        {"ip": "2.2.2.2", "port": 2, "networks": [0], "notify": True},
    ]
    exp = {
        ("1.1.1.1", 1): {
            "ip": "1.1.1.1",
            "port": 1,
            "networks": [0],
            "notify": True,
        },
        ("2.2.2.2", 2): {
            "ip": "2.2.2.2",
            "port": 2,
            "networks": [0],
            "notify": True,
        },
    }
    assert z.convert_secondaries_to_dict(secondaries) == exp


@pytest.mark.parametrize(
    "zone_data,args",
    [
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 1}, id="update_param"),
        pytest.param(
            {"networks": [1]}, {"networks": [1, 2]}, id="update_list"
        ),
        pytest.param(
            {"secondary": {"enabled": True}},
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            id="update_suboption",
        ),
    ],
)
@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.zones.Zone.update")
def test_update(mock_zone_update, ns1_config, zone_data, args):
    m = FakeAnsibleModule("test.zone")

    mock_zone = ns1.zones.Zone(ns1_config, m.name)
    mock_zone.data = m.get_zone_data(**zone_data)

    z = ns1_zone.NS1Zone()
    zone = z.update(mock_zone, args)
    mock_zone_update.assert_called_once_with(**m.get_request_args(**args))
    assert zone != mock_zone


@pytest.mark.parametrize("check_mode", [True, False])
@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.zones.Zone.update")
def test_check_mode(mock_zone_update, ns1_config, check_mode):
    m = FakeAnsibleModule("test.zone")

    mock_zone = ns1.zones.Zone(ns1_config, m.name)
    mock_zone.data = m.get_zone_data(nx_ttl=0)

    z = ns1_zone.NS1Zone()
    args = {"nx_ttl": 1}

    z.module.check_mode = check_mode
    zone = z.update(mock_zone, args)
    if check_mode:
        mock_zone_update.assert_not_called()
        assert zone is None
    else:
        mock_zone_update.assert_called_once_with(**m.get_request_args(**args))
        assert zone != mock_zone


@pytest.mark.parametrize(
    "module_args,exp_params",
    [
        pytest.param({"nx_ttl": 0}, {"nx_ttl": 0}, id="single_param"),
        pytest.param(
            {"nx_ttl": 0, "ttl": None}, {"nx_ttl": 0}, id="none_param",
        ),
        pytest.param(
            {"nx_ttl": 0, "name": "foo"}, {"nx_ttl": 0}, id="ignored_param",
        ),
        pytest.param(
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            {"secondary": {"enabled": True, "primary_ip": "1.1.1.1"}},
            id="suboption",
        ),
        pytest.param(
            {
                "name": "foo",
                "secondary": {
                    "enabled": True,
                    "tsig": {"enabled": True, "name": "key_name"},
                },
            },
            {
                "secondary": {
                    "enabled": True,
                    "tsig": {"enabled": True, "name": "key_name"},
                }
            },
            id="nested_suboption",
        ),
        pytest.param(
            {"secondary": {"enabled": True, "primary_ip": None}},
            {"secondary": {"enabled": True}},
            id="none_suboption",
        ),
        pytest.param(
            {"secondary": {"enabled": None, "primary_ip": None}},
            {},
            id="all_none_suboption",
        ),
    ],
)
def test_sanitize_params(module_args, exp_params):
    z = ns1_zone.NS1Zone()
    params = z.sanitize_params(module_args)
    assert params == exp_params


@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.zones.Zone.load")
def test_get_zone(mock_zone_load, ns1_config):
    zone_name = "test.zone"
    m = FakeAnsibleModule(zone_name)

    mock_zone = ns1.zones.Zone(ns1_config, m.name)
    mock_zone.data = m.get_zone_data()
    mock_zone_load.return_value(mock_zone)

    z = ns1_zone.NS1Zone()
    zone = z.get_zone(zone_name)

    mock_zone_load.assert_called_once()
    zone.data["zone"] = zone_name


@patch("ns1.zones.Zone.delete")
def test_delete(mock_zone_delete, ns1_config):
    m = FakeAnsibleModule("test.zone")

    mock_zone = ns1.zones.Zone(ns1_config, m.name)
    mock_zone.data = m.get_zone_data()

    z = ns1_zone.NS1Zone()
    z.delete(mock_zone)

    mock_zone_delete.assert_called_once_with(**m.get_request_args())


@patch("ns1.NS1.createZone")
def test_create(mock_zone_create, ns1_config):
    args = {"nx_ttl": 1}
    m = FakeAnsibleModule("test.zone")
    m.set_module_args(m.get_args(**args))

    z = ns1_zone.NS1Zone()
    z.create(args)

    mock_zone_create.assert_called_once_with(
        "test.zone", **m.get_request_args(**args)
    )


@pytest.mark.parametrize(
    "mock_zone,exp_changed",
    [
        pytest.param({"zone": "test.zone"}, False, id="update"),
        pytest.param(None, True, id="create"),
    ],
)
@patch("library.ns1_zone.NS1Zone.update_on_change")
@patch("library.ns1_zone.NS1Zone.create")
def test_present(mock_create, mock_update_on_change, mock_zone, exp_changed):
    mock_update_on_change.return_value = (exp_changed, mock_zone)
    z = ns1_zone.NS1Zone()
    test_present = z.present(mock_zone)
    diff = {}
    if len(test_present) == 2:
        changed, zone = test_present
    else:
        changed, zone, diff = test_present
    assert changed == exp_changed
    assert zone is not None
    assert isinstance(diff, dict)
    if mock_zone:
        mock_create.assert_not_called()
        mock_update_on_change.assert_called_once()
    else:
        mock_update_on_change.assert_not_called()
        mock_create.assert_called_once()


@pytest.mark.parametrize(
    "diff,exp_changed",
    [
        pytest.param({"nx_ttl": 0}, True, id="diff"),
        pytest.param({}, False, id="no_diff"),
    ],
)
@patch("library.ns1_zone.NS1Zone.get_changed_params")
@patch("library.ns1_zone.NS1Zone.update")
def test_update_on_change(
    mock_update, mock_get_changed_params, diff, exp_changed
):
    mock_zone = Mock()
    mock_want = Mock()
    mock_get_changed_params.return_value = (diff, diff)
    mock_update.return_value = diff
    z = ns1_zone.NS1Zone()
    changed, zone, changed_params = z.update_on_change(mock_zone, mock_want)
    assert changed == exp_changed
    if exp_changed:
        assert zone != mock_zone
    else:
        assert zone == mock_zone


@pytest.mark.parametrize(
    "mock_zone,exp_changed",
    [
        pytest.param({"name": "zone.test"}, True, id="deletion"),
        pytest.param(None, False, id="no_deletion"),
    ],
)
@patch("library.ns1_zone.NS1Zone.delete")
def test_absent(mock_delete, mock_zone, exp_changed):
    z = ns1_zone.NS1Zone()
    changed = z.absent(mock_zone)
    assert changed == exp_changed


@pytest.mark.parametrize(
    "zone_data, changed, check_mode, exp_result",
    [
        pytest.param(None, False, False, {"changed": False}, id="no_change"),
        pytest.param(
            {"id": 1, "nx_ttl": 0},
            True,
            False,
            {
                "changed": True,
                "id": 1,
                "zone": {"zone": "test.zone", "id": 1, "nx_ttl": 0},
            },
            id="change",
        ),
        pytest.param(
            {"id": 1, "nx_ttl": 0},
            True,
            True,
            {"changed": True},
            id="change_check_mode",
        ),
    ],
)
def test_build_result(zone_data, changed, check_mode, exp_result, ns1_config):
    m = FakeAnsibleModule("test.zone")
    mock_zone = None
    if zone_data:
        mock_zone = ns1.zones.Zone(ns1_config, m.name)
        mock_zone.data = m.get_zone_data(**zone_data)
    z = ns1_zone.NS1Zone()
    z.module.check_mode = check_mode
    result = z.build_result(changed, mock_zone, changed)
    assert result == exp_result
