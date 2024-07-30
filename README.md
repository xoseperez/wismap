WisBlock PIN Mapper CLI
==========================

WisMAP is a CLI port written in python for the RAKwireles Pin Mapper spreadsheet that allows the user to identify potential conflicts between modules in their WisBlock integrations.

## Install / Update

At the time being, there is no proper instalation procedure so the only way it to manually retrieve the code, install the dependencies and import the latest definitions from the original Pin Mapper spreadsheet.

```
git clone https://github.com/xoseperez/wismap
cd wismap
pip install -r requirements.txt
python3 wismap.py import
```

Updating can be done is a similar fashion:

```
cd wismap
git pull
pip install -r requirements.txt
python3 wismap.py import
```

## Running the code

Alternative ways to run the code are available:

* Using `virtualenv` to isolate the dependencies (requires `virtualenv`, example: `apt install python3-virtualenv`):

    ```
    cd wismap
    virtualenv .env
    . .env/bin/activate
    pip install -r requirements.txt
    python3 wismap.py import
    deactivate
    ```

* Using `make` to encapsulate the previous `virtualenv` procedure (requires `virtualenv` and `make`, example: `apt install python3-virtualenv make`):

    ```
    cd wismap
    make import
    ```

## Usage

### Import

The import process downloads the latest WisBlock Pin Mapper spreadsheet (https://downloads.rakwireless.com/LoRa/WisBlock/Pin-Mapper/WisBlock-IO-Pin-Mapper.xlsx) and generates a YAML file with the definitions for each module. It also patches that file with custom definitions for some modules (these patches can be found on the `config.yml` file).

It's mandatory to run it at least the first time you use the utility and advisable to do it after each update.

```
python3 wismap.py import
```

or 

```
make import
```

### List

Simply lists all the modules available.

```
python3 wismap.py list
```

or 

```
make list
```

Example output:

```
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module    ┃ Type      ┃ Description                                             ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ RAK11200  │ WisCore   │ RAK11200 ESP32 WisBlock Core                            │
│ RAK11310  │ WisCore   │ RAK11310 RP4020 WisBlock Core                           │
│ RAK12001  │ WisSensor │ RAK12002 WisBlock Fingerprint Sensor                    │
│ RAK12002  │ WisSensor │ RAK12002 WisBlock RTC Module                            │
│ RAK12003  │ WisSensor │ RAK12003 WisBlock Infrared Temperature Sensor           │
│ RAK12004  │ WisIO     │ RAK12004 WisBlock MQ2 Gas Sensor Module                 │
│ RAK12005  │ WisIO     │ RAK12005 WisBlock Rain Sensor Module                    │
│ RAK12006  │ WisIO     │ RAK12006 WisBlock PIR Module                            │
│ RAK12007  │ WisIO     │ RAK12007 WisBlock Ultrasonic Module                     │
│ RAK12008  │ WisIO     │ RAK12008 CO2 Gas Sensor                                 │
│ RAK12009  │ WisIO     │ RAK12009 WisBlock Alcohol Gas Sensor Module             │
│ RAK12010  │ WisSensor │ RAK12010 WisBlock Ambient Light Sensor                  │
│ RAK12011  │ WisSensor │ RAK12011 WisBlock WP Barometric Sensor                  │
│ RAK12012  │ WisIO     │ RAK12012 WisBlock Heart Rate Sensor                     │
│ RAK12013  │ WisIO     │ RAK12013 WisBlock 3GHz Radar Module                     │
│ RAK12014  │ WisSensor │ RAK12014 WisBlock Laser ToF module                      │
│ RAK12015  │ WisIO     │ RAK12015 WisBlock Vibration Sensor                      │
...

```


### Info

Let's you choose one of the modules and shows basic information for it: description, link to documentation, pin mapping...

```
python3 wismap.py info
```

or 

```
make info
```

Example output:

```
[?] Select module: 
   RAK12002 WisBlock RTC Module
   RAK12003 WisBlock Infrared Temperature Sensor
   RAK12004 WisBlock MQ2 Gas Sensor Module
   RAK12005 WisBlock Rain Sensor Module
   RAK12006 WisBlock PIR Module
   RAK12007 WisBlock Ultrasonic Module
 > RAK12008 CO2 Gas Sensor
   RAK12009 WisBlock Alcohol Gas Sensor Module
   RAK12010 WisBlock Ambient Light Sensor
   RAK12011 WisBlock WP Barometric Sensor
   RAK12012 WisBlock Heart Rate Sensor
   RAK12013 WisBlock 3GHz Radar Module
   RAK12014 WisBlock Laser ToF module

Module: RAK12008
Type: WisIO
Description: RAK12008 CO2 Gas Sensor
Documentation: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK12008
I2C Address: 0x52
Mapping:
┏━━━━━┳━━━━━━━━━━┓
┃ PIN ┃ Function ┃
┡━━━━━╇━━━━━━━━━━┩
│ 1   │ VBAT     │
│ 2   │ VBAT     │
│ 3   │ GND      │
│ 4   │ GND      │
│ 6   │ 3V3_S    │
│ 19  │ I2C_SCA  │
│ 20  │ I2C_SCL  │
│ 22  │ A1       │
│ 29  │ ENABLE   │
│ 32  │ A0       │
│ 37  │ ALERT    │
│ 38  │ EN       │
│ 39  │ GND      │
│ 40  │ GND      │
└─────┴──────────┘
```

### Combine

This options walks you through different menus and lets you choose a base board, a core module and IO and sensor modules for each slot in the base board and then prints out the complet pin mapping for the whole setup along with information about potential conflicts.

```
python3 wismap.py combine
```

or 

```
make combine
```

Example output:

```
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Function ┃ Base board ┃ Core module ┃ IO_A slot ┃ SENSOR_A slot ┃ SENSOR_B slot ┃ SENSOR_C slot ┃ SENSOR_D slot ┃
┃          ┃ (RAK19007) ┃ (RAK4631)   ┃ (EMPTY)   ┃ (RAK12027)    ┃ (BLOCKED)     ┃ (RAK12002)    ┃ (RAK15006)    ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ I2C_ADDR │            │             │           │               │               │               │               │
│ 3V3      │            │ 3V3         │           │               │               │               │               │
│ 3V3_S    │            │             │           │ 3V3_S         │               │               │               │
│ AIN0     │            │ P0.05       │           │               │               │               │               │
│ AIN1     │            │ P0.31       │           │               │               │               │               │
│ BOOT0    │            │             │           │               │               │               │               │
│ GND      │            │ GND         │           │ GND           │               │ GND           │ GND           │
│ I2C1_SCL │            │ P0.14       │           │ I2C_SCL       │               │ I2C_SCL       │               │
│ I2C1_SDA │            │ P0.13       │           │ I2C_SDA       │               │ I2C_SDA       │               │
│ I2C2_SCL │            │ P0.25       │           │               │               │               │               │
│ I2C2_SDA │            │ P0.24       │           │               │               │               │               │
│ IO1      │            │ P0.17       │           │ INT1          │               │               │               │
│ IO2      │            │ P1.02       │           │ INT2          │               │               │               │
│ IO3      │            │ P0.21       │           │               │               │ CLKOUT        │               │
│ IO4      │            │ P0.04       │           │               │               │ INT1          │               │
│ IO5      │            │ P0.09       │           │               │               │               │ WP            │
│ IO6      │            │ P0.10       │           │               │               │               │               │
│ IO7      │            │ P0.28       │           │               │               │               │               │
│ LED1     │            │ P1.03       │           │               │               │               │               │
│ LED2     │            │ P1.04       │           │               │               │               │               │
│ LED3     │            │ P0.02       │           │               │               │               │               │
│ RESET    │            │ RESET       │           │               │               │               │               │
│ RXD0     │            │ P0.19       │           │               │               │               │               │
│ RXD1     │            │ P0.15       │           │               │               │               │               │
│ SPI_CLK  │            │ P0.03       │           │               │               │               │ SPI_CLK       │
│ SPI_CS   │            │ P0.26       │           │               │               │               │ SPI_CS        │
│ SPI_MISO │            │ P0.29       │           │               │               │               │ SPI_MISO      │
│ SPI_MOSI │            │ P0.30       │           │               │               │               │ SPI_MOSI      │
│ SW1      │            │ P1.01       │           │               │               │               │               │
│ TXD0     │            │ P0.20       │           │               │               │               │               │
│ TXD1     │            │ P0.16       │           │               │               │               │               │
│ USB+     │            │ USB+        │           │               │               │               │               │
│ USB-     │            │ USB-        │           │               │               │               │               │
│ VBAT     │            │             │           │               │               │               │               │
│ VBAT_NRF │            │ VBAT_NRF    │           │               │               │               │               │
│ VBAT_SX  │            │ VBAT_SX     │           │               │               │               │               │
│ VBUS     │            │ VBUS        │           │               │               │               │               │
│ VDD      │            │ VDD         │           │ VDD           │               │ VDD           │               │
│ VDD_NRF  │            │ VDD_NRF     │           │               │               │               │               │
│ VIN      │            │             │           │               │               │               │               │
└──────────┴────────────┴─────────────┴───────────┴───────────────┴───────────────┴───────────────┴───────────────┘
Potential conflicts:
- Possible conflict with 3V3_S enable signal if using IO2
Documentation:
- RAK19007 WisBlock Base Board 2nd Gen: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK19007/
- RAK4631 nRF52840 WisBlock Core: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK4631
- RAK12027 WisBlock Earthquake Sensor: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK12027
- RAK12002 WisBlock RTC Module: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK12002
- RAK15006 WisBlock 512kB FRAM Module: https://docs.rakwireless.com/Product-Categories/WisBlock/RAK15006
```

## Contribute

There are several ways to contribute to this project. You can [report](http://github.com/xoseperez/wismap/issues) bugs or [ask](http://github.com/xoseperez/wismap/issues) for new features directly on GitHub.
You can also submit your own new features of bug fixes via a [pull request](http://github.com/xoseperez/wismap/pr).

## License

This project is licensed under [Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0) license.
