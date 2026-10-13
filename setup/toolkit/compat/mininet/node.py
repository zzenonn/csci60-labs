from csci60.net import Host, Switch, Controller, RemoteController  # noqa: F401

# All switch types map to Open vSwitch.
OVSSwitch = OVSKernelSwitch = UserSwitch = OVSBridge = Switch
CPULimitedHost = Host
