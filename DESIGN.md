# Dynamic Presence Integration Design

## Core Purpose

Control lights automatically based on presence detection.

## Basic Functionality

1. Turn on lights when presence detected
2. Turn off lights when room is vacant (after timeout)
3. Allow manual control of lights with state memory
4. Maintain state during Home Assistant restarts
5. Handle connection/sensor failures gracefully

## Configuration Requirements

1. Required:

   - Room name
   - Presence sensor
   - Regular controlled lights

2. Optional:
   - Night mode lights
   - Light sensor

## Controls and Sensors

### Runtime Controls (Device Page)

1. Required Controls

   - Room Automation Switch (master enable/disable)
   - Auto-On Switch (presence-based activation)
   - Auto-Off Switch (vacancy-based deactivation)
   - Night Mode Switch (alternate light control)
   - Night Manual-On Switch (night mode behavior)

2. Status Display
   - State Sensors:
     - Occupancy: Current room occupancy state
     - Night Mode Status: Shows if night mode is currently active
   - Duration Sensors:
     - Occupancy Duration: Time since room became occupied
     - Absence Duration: Time since room became vacant
   - Manual State Sensors:
     - Main Manual States: Lists all main lights and their manual states (ON/OFF)
     - Night Manual States: Lists all night lights and their manual states (ON/OFF)
   - Environmental Sensors:
     - Light Level: Current ambient light level (requires light sensor)

### Configuration Controls (Options Flow)

1. Required Parameters

   - Room name (for identification)
   - Presence sensor (motion/occupancy)
   - Regular lights (primary control)

2. Optional Parameters
   - Night mode lights (alternate set)
   - Light sensor (ambient light)
   - Timeout values (state transitions)
   - Light threshold (automation control)
   - Night mode times (schedule)
   - Adjacent rooms (linked control)

## Basic Functionality Details

### 1. Presence Detection

- Turn on lights immediately when presence detected
- Handle brief detection dropouts:
  - Configurable detection timeout
  - Ignore presence changes shorter than detection timeout
  - Prevent false timeout starts from brief dropouts
- Start timeout countdown only after detection timeout

### 2. Timeout Handling

- Configurable timeout periods
- Countdown starts when presence ends
- Countdown resets if presence detected
- Lights turn off when countdown ends

### 3. Manual Override

- Override automatic control when manually operated
- Clear override when room becomes vacant
- Clear override on next presence detection

### 4. State Persistence

- Remember state across HA restarts
- Maintain timeout countdowns
- Preserve manual override status

## Manual Control Behavior

### Manual State Storage

- Maintains separate manual states for main lights and night lights
- Each light has its own manual state (ON/OFF) that is stored independently
- Manual states determine which lights should turn on when presence is detected
- Manual states are preserved when room becomes vacant
- Switching between modes preserves manual states for each mode independently

### Manual State Updates

1. Automatic Updates (When Presence Detected):

   - If all lights in the active mode are off:
     - Set manual state to ON for all lights in that mode
   - If all lights in the active mode are on:
     - Set manual state to ON for all lights in that mode
   - If lights have mixed states (some on, some off):
     - Set manual states to match current light states

2. Manual Updates (During Presence):
   - When a light is manually turned ON:
     - Light turns on
     - Its manual state is set to ON
   - When a light is manually turned OFF:
     - Light turns off
     - Its manual state is set to OFF
   - Only manual states for the active mode's lights are updated

### Mode Behavior

1. When Presence Detected:

   - Only lights with manual state ON will turn on
   - Lights with manual state OFF remain off
   - Active mode (Main/Night) determines which set of lights and manual states are used

2. When Switching to Night Mode:

   - Main lights turn off
   - Night lights turn on/off according to their stored manual states
   - Main light manual states remain unchanged

3. When Switching to Main Mode:

   - Night lights turn off
   - Main lights turn on/off according to their stored manual states
   - Night light manual states remain unchanged

4. When Room Becomes Vacant (after countdown):
   - All active mode's lights turn off
   - Manual states remain unchanged

### Vacancy Behavior

1. Manual Control During Vacancy:
   - Turning any light on starts the countdown timer
   - Manual states update according to light operations
   - If countdown completes:
     - Lights turn off
     - Manual states remain unchanged
   - If presence detected before countdown completes:
     - Lights remain in their current state
     - Manual states reflect current light states

### Vacancy Behavior

1. Room becomes vacant (after countdown):

   - Lights turn off according to timeout rules
   - Stored states remain unchanged

2. Manual control during vacancy:
   - Turning lights on starts the countdown timer
   - If countdown completes before presence detected:
     - Lights turn off
     - No change to stored states
   - If presence detected before countdown completes:
     - Current light states are stored
     - Normal presence behavior applies
   - Any manual control resets countdown timer

## State Management

### Physical Sensor States

- DETECTED: Sensor physically detects presence
- CLEAR: Sensor reports no physical detection

### Integration Presence States

1. PRESENT

   - Sensor reports DETECTED
   - OR within detection timeout after CLEAR
   - OR within countdown period after detection timeout

2. DETECTION_TIMEOUT

   - Sensor just reported CLEAR
   - Within detection timeout
   - Used to handle brief detection dropouts

3. COUNTDOWN

   - Sensor reports CLEAR
   - Detection timeout has ended
   - Within configured timeout period

4. VACANT
   - Sensor reports CLEAR
   - Detection timeout has ended
   - Countdown period has ended

Important: Lights only turn OFF when state becomes VACANT. All other states maintain lights in their current state.

## Timeout Configuration

Each room has configurable timeout values:

1. Long Timeout (default: 3 minutes)

   - Used during normal operation

2. Short Timeout (default: 30 seconds)

   - Used during night mode

3. Detection Timeout (default: 5 seconds)
   - To prevent false timeout triggers from brief detection dropouts

Note: Timeout values are configured per room during setup

## Optional Features

1. Night Mode

   - Control separate set of lights during night hours
   - Only created if night mode lights are configured
   - Uses configurable start/end times (default: 23:00 - 08:00)
   - Uses short timeout during night hours
   - Uses long timeout outside night hours
   - Switching night mode off mid-operation:
     - Immediately switches to long timeout
     - Continues normal operation

2. Light-based control
   - Only activate lights when light levels are low
   - Only available if light sensor is configured
   - Light threshold of 0 disables light-based control
   - Lights only turn on when light level below threshold
   - Manual control bypasses light threshold check
   - Manual states are always respected regardless of light level

## Room Adjacency

### Basic Rules

- Any room type can be adjacent
- Adjacency is one-way only
- Adjacent rooms are only activated by presence in the room they're connected to
- No chain reactions (adjacent rooms don't activate their own adjacent rooms)

### Configuration

- Available after creating multiple rooms
- Each room can have its own list of adjacent rooms
- Example:
  Office:
  - Can select Living Room as adjacent
  - When office occupied → living room lights on
  - Living Room doesn't need to set Office as adjacent so the Living Room can be occupied without turning on the Office

### Behavior

When a room is occupied:

- Room's own lights turn on
- Adjacent Room lights turn on (respecting their own Auto-On/Off settings)
- Each room follows its own timeout rules
- Each room respects its own manual states
- Night Mode applies to each room independently
- No chain reactions:
  Example:
  - Office has Living Room as adjacent
  - Living Room has Lounge as adjacent
  - When Office is occupied:
    - Living Room lights turn on (because adjacent to Office)
    - Lounge stays off (no chain reaction through Living Room)

Note: Adjacency is one-way and should be configured from the room where presence triggers the adjacent room's lights

## Error Handling

### Sensor Connection Failures

- If presence sensor becomes unavailable:
  - Keep current state
  - Log warning
  - Show error state in UI
- If controlled light unavailable:
  - Continue monitoring presence
  - Skip unavailable light
  - Log warning
  - Show error state in UI

### Detection Dropouts

- Brief dropouts (< detection timeout):
  - Maintain current state
  - No timeout triggered
- Extended dropouts (> detection timeout):
  - Handle as normal presence end
  - Start timeout countdown

Note: Specific implementation details and platform configurations will be defined in INSTRUCTIONS.md

## Runtime State (Storage)

- Manual light states (ON/OFF for each light)
- Switch states
- Timer states
- Current operation mode
- Restored on HA restart
- Persisted during updates

## Configuration State (Config Entry)

- Entity selections
- Timeout values
- Night mode settings
- Adjacent room links
- Requires reload to change
- No runtime data
