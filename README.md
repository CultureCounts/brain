Minimal collectd collector and thresholding alerts system for multiple servers.

Configuration and thresholding functions are in Python.

This collector operates in a hub-and-spoke architecture with the spokes being the servers with collectd instances running on them.

Spokes run collectd and SSH tunnels are set up to each spoke which communicates back to the central hub over the tunnel.

### Configuration ###

The file [brain-config-defaults.py](./brain-config-defaults.py) contains an example configuration.

Each server you connect to can have it's own section, fallbacks will be taken from the `default` section.

### Installation ###

For each host first ensure you have collectd up and running with e.g. `apt-get install collectd`.

For each host that you want to collect from set up the `write_http` collectd plugin.

The collectd plugin is configured as follows, which can go in `/etc/collectd/collectd.conf`:

	LoadPlugin write_http

	<Plugin write_http>
	       <URL "http://localhost:8555">
		       #User "collectd"
		       #Password "secret"
		       #VerifyPeer true
		       #VerifyHost true
		       #CACert "/etc/ssl/ca.crt"
		       #Format "Command"
		       Format "JSON"
		       StoreRates false
	       </URL>
	</Plugin>

Each host should have a `tunnel` configuration set up. An example SSH tunnel script is provided.

### Recommendations ###

A good tool for doing reproduceable deployments is [Ansible](https://ansible.com/).

A good tool for maintaining long-running processes like the tunnels and server is [daemontools](https://unix.stackexchange.com/questions/304415/is-there-a-utility-for-daemonizing-processes-in-user-space).

