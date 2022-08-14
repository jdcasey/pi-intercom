# Python Telegram bot that can record/send audio, for use in Raspberry Pi-driven Intercoms

[![Total alerts](https://img.shields.io/lgtm/alerts/g/jdcasey/pi-intercom.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/jdcasey/pi-intercom/alerts/)[![Pylint](https://github.com/jdcasey/pi-intercom/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/jdcasey/pi-intercom/actions/workflows/pylint.yml)

## Non-PyPI Dependencies

* ffmpeg
* vlc

## Setup

```bash
$ sudo dnf -y install ffmpeg vlc
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -e .
```

## Configuration

Before you do anything, you'll need a Telegram bot. You can get a bot account by chatting with BotFather using a Telegram app. Check out the help for that bot in order to set this up.

In either `/etc/intercompy/config.yaml` or `$HOME/.config/intercompy/config.yaml`, you should create an initial config with just the bot's token:

```yaml
token: 82452345:aslkdjq1049543rsdflkj409tu
```

Once you've done this, setup the chat / group you wish to use for communications. Then, you can add the chat ID to your `config.yaml`:

```yaml
token: 82452345:aslkdjq1049543rsdflkj409tu
chat: 232434254
```

**NOTE:** Consider keeping this group small, since it could have security implications for wherever you mount your bot's microphone!

## Start

```bash
$ intercom
```

**TODO:** I still need to create a systemd startup script for this service.
