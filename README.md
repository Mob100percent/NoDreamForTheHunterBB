# NoDreamForTheHunterBB

A small **Bloodborne private server** written in Python (FastAPI + SQLite). It re-implements the
game's online services so you can run them yourself.

**What works:** Chalice Dungeons, Messages, Specters (Bloodstains), and Illusions (Player White
Phantoms) — for the **EU, US and ASIA** copies of the game.

> **Not for public hosting.** This is the real server, just a **local version**: it was originally
> made as a **private test server** and is meant for **small private servers** that you run yourself.
> It uses **SQLite**, which is fine for that. To host a real **public** server you need to modify it
> first, most importantly by using an actual database server (e.g. PostgreSQL or MySQL) instead of
> SQLite. The code talks to SQLite directly, so this means changing the database code, not just a
> setting.

## Author

**Created by Fahad.** All credit for the server goes to him.
Published to GitHub by [Mob100percent](https://github.com/Mob100percent) with the author's permission.

## Known limitations

- Built for local and small private use, not public hosting (see above).
- The login trusts the account ID sent by the client (no real authentication).
- No rate limiting or abuse protection.
- Debug logging is **on by default** and writes full request headers/bodies to `debug.log`.
  Set `DEBUG=0` to turn it off.
- `init_db.py` always creates `bloodborne.db` in the current folder and ignores the `DB_PATH`
  setting, so the default database name is the one to use.

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Setup

1. **Edit the `ss.info` files.** `ss_info.xml` (EU), `us_ss_info.xml` (US) and `asia_ss_info.xml`
   (Asia) contain `http://YOUR_SERVER_IP:PORT` placeholders. Replace `YOUR_SERVER_IP` with the
   address your client will use to reach the server (e.g. `127.0.0.1` for local testing).
2. **First run only:** create the database:
   ```
   python init_db.py
   ```
3. **Every run:**
   ```
   python main.py
   ```
   The server listens on `0.0.0.0:20443`.

The server serves the region configs at `/bb-eu/ss.info`, `/bb-us/ss.info` and `/bb-asia/ss.info`.

> **Using your own shadNet server:** if you want the game to connect to your shadNet server, replace the
> `<api_SummonData...>` entries (`api_SummonDataCreate`, `api_SummonDataGetList`, `api_SummonDataRemove`
> and `api_SummonDataSummon`) in **all** `ss.info` versions (`ss_info.xml`, `us_ss_info.xml` and
> `asia_ss_info.xml`) with the address of your shadNet server.

### Connecting the game (shadPS4)

The game must be pointed at your server instead of the original one. In shadPS4's
`host_overrides.json`, redirect the game's server address to this server, for example for local testing:

```json
{ "https://ss4.scej-network.jp:20443": "http://127.0.0.1" }
```

Use `127.0.0.1` only when the game and the server run on the same PC. Anyone connecting from another
machine must use the **host's IP address** instead (LAN IP on the same network, or the public IP with
port `20443` forwarded, or a VPN address). The same address must be set in the `ss.info` files.

## Database

The server stores everything in a single SQLite file, `bloodborne.db`, created in the folder you run
it from.

- `python init_db.py` creates the file and its tables, and pre-loads the fixed Chalice Dungeons and a
  welcome notice. Run it **once**, before the first start.
- While the server runs you may also see `bloodborne.db-wal` and `bloodborne.db-shm`. These are normal
  SQLite helper files.
- Main tables: `users`, `sessions`, `characters`, `blood_messages`, `tomb_messages`,
  `wandering_ghosts`, `chair_messages`, `channels` (chalice dungeons), `messenger_shells`, `notices`.
- To back up, stop the server and copy the `.db` file. To start fresh, stop the server, delete the
  `.db` file, and run `python init_db.py` again.

## Accounts and sessions

There is no registration, and you never add users to the database by hand.

- **Accounts:** a user is created automatically the first time a client logs in, based on the account
  ID the game sends. The same account ID always maps to the same user afterwards.
- **Sessions:** every login gives the game a session ID, which it sends with each later request. A
  session is valid for **24 hours**. After that the server rejects it ("Invalid session") and the
  client has to log in again to keep using online features. Nothing is lost when a session expires:
  users, characters and messages stay in the database.
- Change the lifetime with `SESSION_EXPIRY_HOURS` in `config.py`. Expired sessions are not deleted
  from the `sessions` table; they just stop working.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DB_PATH` | `bloodborne.db` | SQLite file location used by the server (see Known limitations) |
| `DEBUG` | `1` | `0` disables request/response logging |
| `BB_ENC_MODE` | `off` | `off`, `optional` or `required` (SENB body encryption) |
| `BB_ENC_KEY_FILE` | `bb_enc_key.txt` | Pre-shared key file, only used if encryption is on |

### Encryption (optional)

`BB_ENC_MODE=optional|required` encrypts request/response bodies between the game client and this
server. It only works if your client supports it, and it uses one shared key, so it does **not**
authenticate individual players. It is **off by default**, so this build works without it. If you
turn it on, keep the key file secret and never commit it.

## Disclaimer

This is an unofficial fan project. It is **not affiliated with or endorsed by** Sony Interactive
Entertainment, FromSoftware or the shadPS4 team. *Bloodborne* and related names are trademarks of their respective
owners. This repository contains **no game files or assets** and does not help you obtain the game;
you need your own legitimate copy. Use at your own risk.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
Copyright (C) 2026 Fahad. This program is free software: you can redistribute it and/or modify it under
the terms of the GPL as published by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. It is distributed WITHOUT ANY WARRANTY.
