# Python Telegram bot that can record/send audio, for use in Raspberry Pi-driven Intercoms

[![Total alerts](https://img.shields.io/lgtm/alerts/g/jdcasey/pi-intercom.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/jdcasey/pi-intercom/alerts/)[![Pylint](https://github.com/jdcasey/pi-intercom/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/jdcasey/pi-intercom/actions/workflows/pylint.yml)

## Pre-Requisites

In order to use this intercom system, you'll need a full Telegram account for it. The main reason for this is to allow multiple intercoms to interact with one another. If the intercoms used bot accounts to access Telegram, they would not be able to see one another.

To establish a Telegram account, you have to be able to associate your account with a phone number that can receive text messages, as this is the main way Telegram verifies the user session.

Once you have that, you'll need to register a new application, using [these instructions](https://core.telegram.org/api/obtaining_api_id). Use the API id and hash below in the configuration section.

## Non-PyPI Dependencies

* ffmpeg
* flac
* vlc

## Setup

First, you need to add some configuration to your Ansible inventory. You'll need a `hosts` file containing a group called `intercoms`:

```ini
[intercoms]
test_intercom
```

Then, in a subdirectory called `host_vars`, you'll need a `test_intercom.yml`. You can copy a starting configuration from `ansible/host_vars/sample.yml`. At a minimum, you need to setup the **`intercompy_telegram_api_id`** and **`intercompy_telegram_api_hash`** variables, to allow you to establish a Telegram session.

**NOTE:** If you would rather not store API id and hash in your configuration, you can set them as environment variables in the shell where you establish the session. See below for more information on that.

Once you've created your host configuration, you can run Ansible to install the intercom using the following command:

```bash
$ cd ansible/
$ ansible-playbook -t first ./install.yml
```

When this command completes, you'll have a **non-functional** intercom on your Pi. To make it functional, you'll need to establish a Telegram session. To do this, SSH into the intercom Pi, then execute the following:

```bash
$ cd intercompy
$ source venv/bin/activate
$ export API_ID=00011212223312123  # If you didn't add it to your host_vars configuration above
$ export API_HASH=adfasdtgasasdfasdafsd  # Again, if it's not in your host_vars
$ intercompy-session-setup
```

This session-setup script will lead you through a series of prompts, including one where you'll need to retrieve a verification code from your mobile phone. When it completes, you'll have a Telegram session saved on the system. Soon after, the systemd script should recover and start the intercom. You'll know this is successful because the intercom will play a message like: **"Your intercom is now online."**

If you need to restart or disable your intercom service, it's called `intercompy`:

```bash
$ sudo systemctl restart intercompy
```

## Usage

Your intercom can have a number of buttons wired into the Pi using GPIO. In fact, this is the only "normal" way to initiate messages from the intercom itself. When you press a button, it looks for a Rolodex entry in your `config.yaml` file that has the matching pin number. If it finds one, it will start recording from the microphone, until enough frames of contiguous silence is detected. When silence is detected, it will end recording, translate the recording to text, and send both to the intended target configured for that pin in the Rolodex. Both text and voice are sent, just in case the target is a person's phone. Sending both gives them more opportunities to understand the message.

When a user wants to send a message to the intercom, first that user has to be in the intercom account's contacts. To establish this, you will need to have the account logged in on a phone or something, then setup a contact for the user. Afterward, any voice message targeting the intercom account will automatically be played. If the user sends a text message instead, that will be rendered to an audio message and played. This way, either mode of communication is supported.

## TO-DO

* **Allow configuration of individual Rolodex entries to turn on/off voice and text variants of a message.** This will be important when sending messages between intercoms, or else the same message will be read out twice.
* **Investigate whether Telegram secret chats are possible.** It would be best if intercoms and their targets could use end-to-end encryption to ensure best privacy.
* **Implement support for feedback LEDs.** It can be hard to tell whether the system is taking a long time to process a message to text, or if something went wrong.
* **Chase out all deadlock situations with better exception handling.** This will be a headless system, so it's important to avoid killing the process or otherwise bricking the device.
* **Mute configuration.** We need a way to manually mute the device, and to setup a sleep schedule for it, just to avoid interrupting a person's sleep.