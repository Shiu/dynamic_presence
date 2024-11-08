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

### Device Page (Runtime Controls)

1. Runtime Controls

   - Room Automation Switch: Enable/disable room automation
   - Auto-On Switch: Control automatic turn on behavior
   - Auto-Off Switch: Control automatic turn off behavior
   - Night Mode Switch: Enable/disable night mode functionality
   - Night Manual-On Switch: Require manual control during night mode

2. Status Display
   - Occupancy State (Occupied/Vacant)
   - Absence Duration (Time since presence lost)
   - Occupancy Duration (Time since room became occupied)
   - Light Level (Current lux value if sensor configured)
   - Night Mode Status (Shows if night mode is currently active based on switch state and time window)

### Options Flow (Configuration)

1. Essential Configuration

   - Room name (required)
   - Presence sensor selection (required)
   - Regular lights selection (required)

2. Advanced Configuration
   - Night mode lights selection
   - Light sensor selection
   - Timeout Values:
     - Long timeout (normal operation)
     - Short timeout (night mode)
     - Detection timeout
   - Light threshold (if sensor configured)
   - Night mode times (start/end)
   - Adjacent room selection

### Data Flow Architecture

1. Runtime State Flow

   - Device controls → Storage → Runtime state
   - Manual light states → Storage → Light states
   - Presence events → State machine → Runtime state
   - No options updates during operation

2. Configuration Flow

   - Options flow → Config entry
   - Config changes require reload
   - No runtime state storage in options

3. Storage Usage
   - Runtime states only
   - Manual light states
   - Timer states
   - No configuration storage

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
     - Night Mode: Enable/disable night mode functionality
     - Night Manual-On: Require manual control during night

   - Number Platform

     - Long Timeout: Room vacancy timeout
     - Short Timeout: Night mode vacancy timeout
     - Light Threshold: Minimum light level for automation

   - Sensor Platform

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

## State Management and Data Flow

### Storage Structure

```python
@dataclass
class DynamicPresenceStorageData:
    """Storage data structure."""
    states: dict  # Runtime entity states
    manual_states: dict  # Manual light states
```

### Data Flow Architecture

1. Storage Helper (`storage.Store`)

   - Primary source of truth for runtime states
   - Located at `.storage/dynamic_presence.{entry_id}`
   - Handles:
     - Entity states (numbers, switches, times)
     - Manual light states
     - Timer-related states
   - No integration reload on updates

2. Config Entry

   - Stores static configuration
   - Room name only
   - Located in `.storage/core.config_entries`

3. Options Entry
   - Stores user configuration
   - Entity selections (sensors, lights)
   - Initial setup parameters
   - Must stay in sync with storage helper

### State Synchronization Rules

1. Device Page → Storage → Options

   ```
   UI Change → Update Storage → Update Runtime State
            → NO direct Options/Config updates during timers
   ```

2. Options Page → Config → Storage

   ```
   Options Change → Update Options Entry
                 → Update Storage
                 → Update Runtime State
   ```

3. Startup Sequence

   ```
   Load Storage → Update Runtime State
               → Sync to Options if needed
               → Restore timers
   ```

4. Options Flow
   ```
   Open Options → Load current states from Storage
   Save Options → Update Options Entry
                → Update Storage
                → Update Runtime State
   ```

### Implementation Notes

1. Storage Helper is used for:

   - All runtime state changes
   - Timer state persistence
   - Manual light state tracking
   - Any frequently changing values

2. Options Entry is used for:

   - Entity configurations
   - User preferences
   - Initial setup parameters

3. Config Entry is used for:

   - Room name
   - Integration identification

4. State Updates:
   - Device page updates only use Storage Helper
   - Options page updates use both Storage and Options Entry
   - Never update Config/Options during timer operations
