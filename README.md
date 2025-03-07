# followspot-psn

Solution for controlling followspots, and sending the position data to ma3 over
[posistagenet (PSN)](https://posistage.net/). It uses
[psn-py](https://github.com/vyv/psn-py) to do PSN stuff.

### Deployment

**TLDR**: `docker compose up --build` on a Linux machine.

> [!NOTE]
> Why Linux? This is because PSN uses multicast to transmit positional data to
> ma3. On linux this is done using host networking driver. However the host
> networking driver on macOS or windows will only allow broadcasting on the
> docker linux VM. It could probably be done using some fancy routing/bridge
> setup with the docker VM.

This opens a webserver on port 8000 where you can control the PSN trackers. PSN
data is multicasted on `236.10.10.10:56565`. Tracker positions can also be
updated using OSC, by default OSC listens on port 9000. The OSC endpoint expects
data on `/Tracker/{trackerid}` with three floats specifying x, y and z value.

Currently all configuration is done in the source files, most notably in
[psn_server.py](backend/psn_server.py).

The rest of the functionality is documented in the code.
