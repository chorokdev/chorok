# Chorok - High quality Discord music bot

## Config guide
```json5
{
  "mode_name": { // You can run with `python3 main.py <mode_name>`
    "token": {
      "discord": "",
      "koreanbots": "" // Blank if you aren't going to use koreanbots
    },
    "node": [
      {
        "local": false, // true if you are going to use local node
        "host": "chorok-node", // Host of node
        "port": 8000, // Port of node
        "password": "hellodiscodo" // Password of node
      }
    ],
    "slash_command_guild": null, // null: global, string: that guild only
    "cache": {
      "host": "chorok-cache", // Host of redis server
      "port": 6379 // Port of redis server
    }
  }
}
```

## How to run?
> Support **Python 3.9.\*** or higher
1. setup config with config.json (see [config guide](#config-guide))
2. install deps with `pip(3.*) install -r requirements.txt`
3. run discodo node
4. run bot with `python(3.*) main.py <mode>`

## Thanks to
[eunwoo1004](https://github.com/eunwoo1104): Maintainer of [dico](https://github.com/dico-api/dico)  
[fxrcha](https://github.com/fxrcha): Designer of web dashboard(comming soon)
