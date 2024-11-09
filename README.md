# Dynamic Presence

Dynamic Presence provides automation of lights based on room presence.

## Features

- Presence detection with configurable timeouts
- Night mode with time-based and manual control
- Automatic light control based on presence
- Smart state management for manual overrides
- Configurable detection and countdown timers

## Configuration

TODO: Add configuration instructions

### Required Configuration

- Presence Sensor (binary sensor)
- Main Lights (list of light entities)

### Optional Configuration

- Night Lights (separate set of lights for night mode)
- Light Sensor (for ambient light detection)
- Night Mode Start/End Times

## Options

### Basic Settings

| Option            | Type   | Default | Description                                 |
| ----------------- | ------ | ------- | ------------------------------------------- |
| Presence Sensor   | Entity | None    | Binary sensor for presence detection        |
| Main Lights       | List   | None    | Lights to control during normal operation   |
| Night Lights      | List   | None    | Lights to control during night mode         |
| Light Sensor      | Entity | None    | Optional sensor for ambient light detection |
| Detection Timeout | Number | 30      | Seconds to wait before starting countdown   |
| Long Timeout      | Number | 300     | Countdown duration during normal operation  |
| Short Timeout     | Number | 60      | Countdown duration during night mode        |
| Light Threshold   | Number | 10      | Light level threshold for automation        |

### Night Mode Settings

| Option           | Type | Default | Description                    |
| ---------------- | ---- | ------- | ------------------------------ |
| Night Mode Start | Time | 20:00   | Time when night mode can start |
| Night Mode End   | Time | 08:00   | Time when night mode can end   |

## Operation Logic

### Presence Detection

The integration uses a binary sensor to detect room occupancy:

- When presence is detected, the room enters OCCUPIED state
- When presence is lost, it enters DETECTION_TIMEOUT
- After detection timeout, it enters COUNTDOWN
- After countdown expires, room becomes VACANT

### Light Control

- Lights can be configured to turn ON/OFF based on presence
- Different sets of lights are used based on night mode status
- Manual control states are preserved

### Night Mode

Night mode combines two conditions:

- Time-based: Current time is between Start and End times
- Manual control: Night Mode switch is enabled

Night mode affects:

- Which set of lights are controlled (main vs night)
- Countdown duration (long vs short timeout)

### Manual Override

The integration tracks ON/OFF states for each light, but only updates these states during room occupancy:

- Each light has its own ON/OFF state in each mode:

  - Main mode lights have their own states
  - Night mode lights have their own states
  - States are independent between modes

- Manual states are only updated when the room is occupied:

  - Turning a light OFF during occupancy sets its state to OFF
  - Turning a light ON during occupancy sets its state to ON
  - These states determine which lights turn on next time presence is detected

- Manual control during vacancy:

  - Turning lights on/off starts the countdown timer
  - If presence is detected before countdown ends:
    - Current light states become the new manual states
  - If countdown completes without presence:
    - Lights turn off
    - No manual states are changed

- Manual states default to ON:
  - When a room is first configured
  - When a light hasn't been used in a mode before
  - When all lights in the active mode are turned on/off during occupancy

## TODO

- [ ] Implement logic for room adjacency
- [ ] Improve light control logic
- [ ] Persist manual states across restarts
- [ ] Adaptive timeouts based on usage patterns
- [ ] Add required Home Assistant tests:
  - [ ] Unit tests for all components
  - [ ] Integration tests for core functionality
  - [ ] End-to-end tests for config/options flow
  - [ ] Test coverage must be >75%
- [ ] Create integration logo:
  - [ ] Must be a vector image (SVG format)
  - [ ] Square aspect ratio
  - [ ] Transparent background
  - [ ] Follow Home Assistant brand guidelines
  - [ ] Include both light and dark versions
  - [ ] Provide in required sizes (256x256, 512x512)

## BUGS

- This is a work in progress, so expect lots of bugs
