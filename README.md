# Chorok - High quality Discord music bot
Rewrite with [dico](https://github.com/dico-api/dico)

## Config guide
```json5
{
  "mode_name": { // You can run with `python3 main.py <mode_name>`
    "tokens": {
      "discord": "",
      "koreanbots": "" // Blank if you aren't going to use koreanbots
    },
    "node": [
      {
        "local": false, // true if you are going to use local node
        "host": "discodo", // Host of node
        "port": 8000, // Port of node
        "password": "hellodiscodo" // Password of node
      }
    ],
    "slash_command_guild": null // null: global, string: that guild only
  }
}
```

## How to run?
> Only support **Python 3.9.n** or higher
1. setup config with config.json (see [config guide](#config-guide)
2. install deps with `pip(3.*) install -r requirements.txt`
3. run discodo node
4. run bot with `python(3) main.py <mode>`
