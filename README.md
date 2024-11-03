# Dynamic Presence

Dynamic Presence provides automation of devices based on room presence.

## Features

- Presence detection with configurable timeout thresholds
- Night mode
- Light-level based automation
- Smart manual override system
- Configurable timeouts

## Configuration

### Initial Setup

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Dynamic Presence"
4. Follow the configuration flow

### Required Configuration

- Presence Sensor (binary sensor or device tracker)
- Controlled Entities (lights, switches, etc.)

### Optional Configuration

- Light Sensor
- Night Mode Controlled Entities
- Night Mode Settings

## Options

### Basic Settings

| Option                  | Type   | Default | Description                                  |
| ----------------------- | ------ | ------- | -------------------------------------------- |
| Enable                  | Switch | On      | Enable/disable the integration               |
| Manage On Presence      | Switch | On      | Turn on devices when presence detected       |
| Manage On Clear         | Switch | On      | Turn off devices when timeout reached        |
| Presence Timeout        | Number | 180     | Seconds before turning off after no presence |
| Short Absence Threshold | Number | 10      | Grace period for brief absences              |
| Active Room Threshold   | Number | 600     | Seconds to consider room as active           |
| Active Room Timeout     | Number | 600     | Timeout for active rooms                     |
| Light Threshold         | Number | 20      | Light level threshold for automation         |
| Remote Control Timeout  | Number | 60      | Timeout for manual control in empty room     |

### Night Mode Settings

| Option                          | Type   | Default   | Description                         |
| ------------------------------- | ------ | --------- | ----------------------------------- |
| Night Mode Enable               | Switch | Off       | Enable night mode features          |
| Night Mode Start                | Time   | 23:00     | Night mode start time               |
| Night Mode End                  | Time   | 07:00     | Night mode end time                 |
| Night Mode Scale                | Number | 0.5       | Multiply timeouts during night mode |
| Night Mode Override On Presence | Switch | Off       | Disable auto-on during night        |
| Night Mode Entities Add Mode    | Select | Exclusive | How to handle night mode entities   |

## Configuration Logic

### Presence Detection

The integration uses presence sensors to detect occupancy in a room. When presence is detected and `Manage On Presence` is enabled, controlled entities will turn on (subject to light level if a light sensor is configured).

- `Short Absence Threshold`: Prevents devices from turning off during brief absences (like walking between rooms), and also protects against short dropouts of presence detection
- `Presence Timeout`: How long to wait after presence is lost before turning off devices
- `Active Room Threshold`: Time required for continuous presence before considering a room "active"
- `Active Room Timeout`: Longer timeout period for rooms that were previously "active"

### Light Level Control

If a light sensor is configured:

- Lights will only turn on automatically if the room is darker than `Light Threshold`
- This prevents unnecessary light activation during daylight hours

### Manual Control

The integration includes smart handling of manual device control:

- `Remote Control Timeout`: If you manually turn on lights in an empty room, they will turn off after this timeout unless presence is detected
- Manual device states are remembered while the room is occupied
- When leaving a room:
  - If all lights were off, states clear immediately
  - If all lights were on, states clear after presence timeout
  - If lights were mixed (both on and off), states are preserved

### Night Mode

Night mode provides additional control during specified hours:

- `Night Mode Scale`: Multiplies all timeouts during night mode (0.5 = half the normal duration)
- `Night Mode Override On Presence`: Prevents automatic device activation during night hours
- `Night Mode Entities Add Mode`:
  - Exclusive: Only night mode entities are controlled
  - Additive: Night mode entities are added to normal entities

## TODO

This is very early stages, so some initial testing will be required before any future plans are finalized.
