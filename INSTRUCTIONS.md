# Dynamic Presence Integration

## Architecture

### State Machine States

- VACANT: No presence detected, all timeouts expired
- OCCUPIED: Presence detected
- DETECTION_TIMEOUT: Within detection timeout after presence lost
- COUNTDOWN: Within countdown period after detection timeout

### Data Flow

1. Presence Sensor Changes → Coordinator Update → State Machine → Light Control
2. Each state change triggers appropriate light updates
3. Manual control updates stored states when room has presence
4. Timeout periods and thresholds configurable per room

### Files Structure

├── **init**.py # Integration setup
├── config_flow.py # Config flow
├── const.py # Constants and config keys
├── manifest.json # Integration manifest
├── number.py # Number platform entities
├── select.py # Select platform for light selection
├── sensor.py # Sensor platform entities
├── switch.py # Switch platform entities
├── time.py # Time platform entities
├── presence_control.py # State machine and control logic
├── coordinator.py # Data coordinator
├── services.yaml # Service definitions
├── strings.json # String translations
└── translations/
└── en.json # English translations

## Configuration

### Config Flow

Initial setup requires only the essential fields:

- Room name (required)
- Presence sensor (required)
- Controlled lights (required)

### Options Flow

After initial setup, additional features can be configured:

1. Light Control

   - Night Mode lights
   - Light sensor
   - Light threshold

2. Timing

   - Long timeout
   - Short timeout
   - Detection timeout
   - Night Mode start/end times

3. Advanced
   - Adjacent rooms
   - Auto-On/Off settings
   - Night Mode settings

### Device Page

Runtime controls and sensors:

1. Switches

   - Room Automation
   - Auto-On
   - Auto-Off
   - Night Mode
   - Night Manual-On

2. Numbers

   - Long timeout
   - Short timeout
   - Light threshold

3. Sensors
   - Occupancy State (Occupied/Vacant)
   - Absence Duration (Time since presence lost after detection timeout)
   - Occupancy Duration (Time since room became occupied)
   - Light Level (Lux value from light sensor)
   - Night Mode Status (On/Off)

## Development Guidelines

### State Machine Implementation

1. State Transitions

   - When presence lost: OCCUPIED → DETECTION_TIMEOUT
   - When presence detected during timeout: DETECTION_TIMEOUT → OCCUPIED
   - When detection timeout expires: DETECTION_TIMEOUT → COUNTDOWN
   - When presence detected during countdown: COUNTDOWN → OCCUPIED
   - When countdown expires: COUNTDOWN → VACANT
   - When presence detected: Any State → OCCUPIED

2. Timer Management

   - Detection timeout starts when presence lost
   - Countdown starts after detection timeout
   - All timers cancel on presence detection
   - Timer values configurable per room

3. Event Handling
   - Presence sensor state changes
   - Manual light control
   - Timer expiration
   - Configuration changes

### Coordinator Pattern

1. Data Management

   - Stores room configuration
   - Manages light states
   - Handles timer scheduling
   - Maintains state machine

2. Entity Updates

   - Propagates state changes to entities
   - Updates sensor values
   - Manages light control
   - Handles adjacent room updates

3. State Persistence
   - Saves manual light states
   - Preserves room configuration
   - Maintains timers across restarts

### Entity Creation

1. Platform Implementations

   - Switch Platform

     - Automation: Enable/disable room automation
     - Auto-On: Control automatic turn on
     - Auto-Off: Control automatic turn off
     - Night Mode: Enable/disable night mode
     - Night Manual-On: Require manual control during night

   - Number Platform

     - Long Timeout: Room vacancy timeout
     - Short Timeout: Night mode vacancy timeout
     - Light Threshold: Minimum light level for automation

   - Sensor Platform

     - Occupancy: Room occupancy state
     - Absence Duration: Time since presence lost
     - Occupancy Duration: Time room occupied
     - Light Level: Current light level
     - Night Mode Status: Night mode state

   - Time Platform
     - Night Mode Start: When night mode begins
     - Night Mode End: When night mode ends

2. Entity Naming

   Format: [domain].dynamic*presence*[room_name]\_[entity_id]
   Examples:

   - switch.dynamic_presence_living_room_automation
   - number.dynamic_presence_living_room_long_timeout
   - sensor.dynamic_presence_living_room_occupancy

3. State Updates

   a. Switch Platform Updates

   - Automation: Updated by user, affects all automation
   - Auto-On: Updated by user or Night Manual-On, affects automatic turn on behavior
   - Auto-Off: Updated by user, affects automatic turn off behavior
   - Night Mode: Updated by user or time schedule
   - Night Manual-On: Updated by user, affects night mode behavior and Auto-On

   b. Number Platform Updates

   - Long/Short Timeout: Updated by user, applied immediately
   - Light Threshold: Updated by user, applied immediately

   c. Sensor Platform Updates

   - Occupancy: Updated when state machine changes state
   - Absence Duration: Updated every second when room vacant (after detection timeout)
   - Occupancy Duration: Updated every second when room occupied
   - Light Level: Updated when light sensor reports new value
   - Night Mode Status: Updated when night mode state changes

   d. Time Platform Updates

   - Night Mode Start/End: Updated by user, triggers night mode changes

   e. Coordinator Responsibilities

   - Manages all state updates through single point
   - Ensures consistent state across entities
   - Handles update scheduling (timers, durations)
   - Propagates changes to affected entities
   - Maintains state history

### Error Handling

1. Sensor Connection Failures
   - If presence sensor becomes unavailable:
     - Keep current state
     - Log warning
     - Show error state in UI
   - If controlled light unavailable:
     - Continue monitoring presence
     - Skip unavailable light
     - Log warning
     - Show error state in UI
