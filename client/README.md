# FFXI Packet Eater Client

_Based on https://github.com/HealsCodes/XIPivot_

`/client/ashita` and `/client/windower/`

Ashita-v4 and Windower-v4 plugins which non-intrusively collects and sends packet data to the cloud.

### Usage (Ashita-v4)

Download the pre-compiled plugins here: [here](https://github.com/zach2good/PacketEater/raw/main/client/bin/Ashita/PacketEater.dll).

- Copy in compiled DLL to `<ashita>/plugins/`
- Add `/load PacketEater` to the bottom of your `<ashita>/scripts/default.txt` file

### Usage (Windower-v4)

Download the contents of the addon folder here: [here](https://github.com/zach2good/PacketEater/raw/main/client/bin/Windower/).

- Place the downloaded files in your addons folder:

```txt
Windower/
    addons/
        PacketEater/
            lib/
                _PacketEater.dll
            PacketEater.lua
```

- Add `lua load PacketEater` to the bottom of your `<windower>/scripts/init.txt` file

### Building

```sh
mkdir build
cmake -S . -B build -A Win32
cmake --build build
```

### NOTES

- The pre-compiled DLL may be flagged by your antivirus. This is a false positive, sorry! If you're unsure about the DLL, feel free to poke around in the code and to build it locally.
- Nothing bad will happen if you use this (or leave it on) while playing on private servers, the plugin will just be idle and not collect or send any information.

### Thanks

- atom0s([Ashita-v4beta](https://github.com/AshitaXI/Ashita-v4beta), [ExamplePlugin](https://github.com/AshitaXI/ExamplePlugin))
- Heals ([XIPivot](https://github.com/Shirk/XIPivot))
- Windower Team ([Website](https://www.windower.net/), [GitHub](https://github.com/Windower))
