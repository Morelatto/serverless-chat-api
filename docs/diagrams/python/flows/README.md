# 🔄 Flow Diagrams

User journeys and temporal sequences.

## Diagrams

### 1. Request Journey
**File**: `02_request_journey.png`

Complete request lifecycle from user to response:
- Authentication → Rate limiting → Validation
- Cache split: 90% hits (17ms) vs 10% misses (820ms)
- Visual weight shows traffic distribution

**Key Insight**: Cache hits are 48x faster than cache misses.

### 2. Authentication Flow
**File**: `06_authentication_flow.png`

JWT token lifecycle:
- Login with credentials → Generate JWT
- Token validation on each request
- 30-minute TTL with refresh capability

**Key Insight**: Stateless authentication enables horizontal scaling.

### 3. Startup Sequence
**File**: `09_startup_sequence.png`

Application initialization order:
- Load config → Initialize services → Start API
- Parallel initialization where possible
- Total startup time: 50ms

**Key Insight**: Fast startup enables quick deployments and scaling.

## Visual Conventions
- **Sequential flow** shows temporal order
- **Parallel branches** indicate concurrent operations
- **Timing annotations** show performance characteristics
