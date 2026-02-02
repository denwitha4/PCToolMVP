# PC Planner Module - Implementation Summary

## Overview

This document details the implementation of the PC Planner module for the PC building/flipping application. The planner is a profit-aware, inventory-aware decision engine that helps optimize margins and plan builds.

## Files Created/Modified

### New Files
1. **`routes/planner.py`** - Complete planner API implementation (600+ lines)
2. **`PLANNER_README.md`** - Comprehensive user documentation
3. **`test_planner.py`** - Test script for API endpoints
4. **`PLANNER_IMPLEMENTATION.md`** - This document

### Modified Files
1. **`database.py`** - Enhanced Build and BuildComponent models
2. **`main.py`** - Added planner router

## Requirements Coverage

### ✅ 1A. Per-Component Margin Visibility

**Implementation**: `calculate_component_metrics()` function in `routes/planner.py`

Each component exposes:
- ✅ Component cost (from inventory or manual)
- ✅ Component MSRP
- ✅ Component profit margin (absolute $ and %)
- ✅ Component contribution to total build cost (%)

**Database Fields**:
- `BuildComponent.cost_at_time` - Unit cost
- `BuildComponent.quantity` - Quantity used
- Computed properties: `total_component_cost`, `component_profit`, `component_margin_percentage`

**API Response**:
```json
{
  "unit_cost": 399.99,
  "total_cost": 399.99,
  "unit_msrp": 549.99,
  "total_msrp": 549.99,
  "profit_absolute": 150.00,
  "profit_margin_percentage": 27.27,
  "cost_contribution_percentage": 30.77
}
```

### ✅ 1B. Target Profit Mode

**Implementation**: `Build` model properties and `calculate_build_metrics()` function

User can define:
- ✅ Target profit as fixed dollar amount
- ✅ Target profit as percentage margin

**Database Fields**:
- `Build.target_profit_amount` (Float, nullable)
- `Build.target_profit_percentage` (Float, nullable)

**Computed Properties**:
- `Build.meets_target_profit` - Boolean, checks if target is met
- `Build.max_allowable_cost` - Maximum cost to meet target
- `Build.projected_profit` - Calculated profit
- `Build.projected_margin_percentage` - Calculated margin %

**Planner Behavior**:
- ✅ Calculates maximum allowable total build cost
- ✅ Indicates whether build meets/under/over target
- ✅ Surfaces which components are causing target misses
- ✅ Updates in real time
- ✅ Does NOT mutate inventory
- ✅ Does NOT auto-change parts (only informs)

**API Endpoint**: `GET /api/planner/builds/{build_id}/target-profit-analysis`

Returns:
```json
{
  "target_status": "meets|under_target|over_budget",
  "meets_target": true,
  "max_allowable_cost": 1329.95,
  "current_total_cost": 1299.93,
  "cost_variance": 30.02,
  "over_budget_amount": null,
  "problematic_components": []
}
```

### ✅ 5A. Inventory-Aware Component Selection

**Implementation**: `get_available_inventory()` endpoint and component metrics

The planner distinguishes between:
- ✅ Parts that exist in inventory
- ✅ Parts that do NOT exist in inventory

**Database Fields**:
- `BuildComponent.lot_id` (nullable) - Links to inventory
- `BuildComponent.is_external` (Boolean) - Marks non-inventory parts

**Planner Behavior**:
- ✅ Shows available inventory quantity
- ✅ Highlights components already owned (`is_inventory_backed`)
- ✅ If selected quantity exceeds inventory:
  - ✅ Allows selection
  - ✅ Marks excess as externally sourced
- ✅ Supports hybrid builds (some inventory, some external)
- ✅ Inventory-backed vs external tracked separately

**API Endpoints**:
- `GET /api/planner/inventory-available?category=GPU` - Get available inventory
- Component metrics include:
  ```json
  {
    "is_inventory_backed": true,
    "is_external": false,
    "inventory_available": 3,
    "inventory_reserved": 1,
    "has_sufficient_inventory": true
  }
  ```

### ✅ 5B. Soft Reservation Mode

**Implementation**: `soft_reserve_inventory()` and `release_inventory_reservation()` functions

User can:
- ✅ Soft-reserve inventory parts for a specific build

**Rules**:
- ✅ Reduces available inventory
- ✅ Does NOT mark items as sold
- ✅ Can be released or modified
- ✅ Reservation is reversible
- ✅ No hard inventory mutation without confirmation

**Storage**:
- ✅ Which inventory lots are reserved (`InventoryLot.assigned_build_id`)
- ✅ Quantity reserved per lot (`InventoryLot.quantity_reserved`)
- ✅ Movement audit trail (`InventoryMovement` with type RESERVE/RELEASE)

**API Endpoints**:
- `POST /api/planner/builds/{build_id}/reserve` - Manual soft reserve
- `DELETE /api/planner/builds/{build_id}/reserve/{lot_id}` - Release reservation
- `GET /api/planner/builds/{build_id}/reservations` - View all reservations
- Automatic reservation when adding inventory-backed components
- Automatic release when deleting components or build

**Behavior**:
- Enables planning multiple builds simultaneously without conflicts
- Inventory status changes to `RESERVED` when quantity_reserved > 0
- Automatically reverts to `IN_STOCK` when all reservations released

## Data Models

### Build Entity (Enhanced)

**New Fields**:
- `target_profit_amount` (Float, nullable)
- `target_profit_percentage` (Float, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Computed Properties**:
```python
@property
def total_cost(self): ...
@property
def total_msrp(self): ...
@property
def projected_profit(self): ...
@property
def projected_margin_percentage(self): ...
@property
def meets_target_profit(self): ...
@property
def max_allowable_cost(self): ...
```

### BuildComponent Entity (Enhanced)

**New Fields**:
- `is_external` (Boolean, default=False)
- `quantity_from_inventory` (Integer, default=0)
- `quantity_external` (Integer, default=0)
- `external_cost` (Float, nullable)

**Computed Properties**:
```python
@property
def total_msrp(self): ...
@property
def total_component_cost(self): ...
@property
def component_profit(self): ...
@property
def component_margin_percentage(self): ...
@property
def cost_contribution_to_build(self): ...
@property
def is_inventory_backed(self): ...
@property
def has_sufficient_inventory(self): ...
```

## Calculation Rules (Strict Compliance)

### ✅ Dynamic Calculations
- ✅ Profit, margin, totals computed dynamically
- ✅ Do NOT persist computed values
- ✅ All calculations in model properties or API functions

### ✅ Inventory Safety
- ✅ Inventory quantities never go negative
- ✅ Validation in `soft_reserve_inventory()`:
  ```python
  available = lot.quantity_available
  if quantity > available:
      raise HTTPException(status_code=400, detail="Insufficient inventory")
  ```

### ✅ External Components
- ✅ External components do NOT affect inventory counts
- ✅ Check `is_external` flag before inventory operations

## API Logic

### Planner Operations Supported

1. ✅ **Creating a build** - `POST /api/planner/builds`
2. ✅ **Adding/removing components** - `POST/DELETE /api/planner/builds/{id}/components`
3. ✅ **Switching components between inventory/external** - `PUT /api/planner/builds/{id}/components/{cid}`
4. ✅ **Soft-reserving inventory parts** - `POST /api/planner/builds/{id}/reserve`
5. ✅ **Releasing reservations** - `DELETE /api/planner/builds/{id}/reserve/{lot_id}`
6. ✅ **Running target profit analysis** - `GET /api/planner/builds/{id}/target-profit-analysis`
7. ✅ **Fetching planner state with all computed fields** - `GET /api/planner/builds/{id}`

## Hard Rules Compliance

### ✅ Safety Constraints

1. ✅ **Do NOT auto-buy or auto-adjust parts**
   - All component additions require explicit API calls
   - No automatic part selection or purchasing

2. ✅ **Do NOT hard-reserve or sell inventory from planner**
   - Planner only soft-reserves (quantity_reserved)
   - Selling requires separate sales flow
   - Reservations are reversible

3. ✅ **Planner must be safe for concurrent builds**
   - Each build tracks its own reservations
   - Reservations reduce available inventory globally
   - No race conditions (transactional database operations)

4. ✅ **Planner logic must be deterministic and auditable**
   - All calculations use pure functions
   - Inventory movements logged in `InventoryMovement` table
   - No random or time-dependent behavior
   - Same inputs always produce same outputs

## API Architecture

### Route Structure
```
/api/planner/
  POST   /builds                              # Create build
  GET    /builds                              # List all builds
  GET    /builds/{id}                         # Get build details
  PUT    /builds/{id}                         # Update build
  DELETE /builds/{id}                         # Delete build
  
  POST   /builds/{id}/components              # Add component
  PUT    /builds/{id}/components/{cid}        # Update component
  DELETE /builds/{id}/components/{cid}        # Remove component
  
  GET    /builds/{id}/target-profit-analysis  # Analyze target profit
  GET    /builds/{id}/reservations            # View reservations
  
  POST   /builds/{id}/reserve                 # Soft reserve
  DELETE /builds/{id}/reserve/{lot_id}        # Release reservation
  
  GET    /inventory-available                 # Browse inventory
```

### Authentication
- All endpoints require user authentication via `get_current_user_id()`
- All queries scoped to authenticated user
- No cross-user data leakage

## Testing

### Test Coverage

**Test Script**: `test_planner.py`

Tests:
1. ✅ Create build with target profit
2. ✅ Get available inventory
3. ✅ Get all builds
4. ✅ Get build details
5. ✅ Add inventory-backed component
6. ✅ Add external component
7. ✅ Target profit analysis
8. ✅ View reservations
9. ✅ Update target profit
10. ✅ Delete build (cleanup)

### Manual Testing Scenarios

1. **Hybrid Build**:
   - Add 4 components from inventory
   - Add 4 external components
   - Verify all metrics calculate correctly

2. **Target Profit Mode**:
   - Set 30% target
   - Add components until over budget
   - Verify "over_budget" status and problematic components surfaced

3. **Reservation Management**:
   - Create 3 builds
   - Reserve overlapping inventory
   - Verify available quantities decrease appropriately
   - Delete builds, verify reservations released

4. **Component Switching**:
   - Add component as external
   - Switch to inventory-backed
   - Verify reservation created
   - Switch back to external
   - Verify reservation released

## Migration Strategy

### Database Migration

**Function**: `_migrate_planner_fields()` in `database.py`

Adds new fields to existing tables:
- `builds`: target_profit_amount, target_profit_percentage, created_at, updated_at
- `build_components`: is_external, quantity_from_inventory, quantity_external, external_cost

**Execution**: Runs automatically on `init_db()` during server startup

**Safety**: Uses `ALTER TABLE` with existence checks, no data loss

## Integration Points

### With Existing Inventory System
- ✅ Reads product catalog (does not modify)
- ✅ Reads inventory lots (does not modify quantities directly)
- ✅ Manages soft reservations via `quantity_reserved` field
- ✅ Logs movements in `InventoryMovement` table
- ✅ Does NOT mutate `quantity_on_hand`

### With Existing Builder System
- ✅ Reuses `Build` and `BuildComponent` tables
- ✅ Compatible with existing `/api/builder` routes
- ✅ Shares `BuildStatus` enum
- ✅ Planner adds new fields but doesn't break existing code

## Key Design Decisions

### 1. Soft Reservations via `quantity_reserved`
- Uses existing `InventoryLot.quantity_reserved` field
- Maintains audit trail via `InventoryMovement`
- Reversible and safe for concurrent builds

### 2. Computed Properties for Metrics
- All financial metrics calculated dynamically
- No persisted denormalized data
- Ensures consistency and accuracy

### 3. External Components via `is_external` Flag
- Simple boolean flag to distinguish sourcing
- Allows hybrid builds (inventory + planned purchases)
- No inventory impact when `is_external = True`

### 4. Target Profit as Optional Fields
- Separate fields for amount vs percentage
- Mutually exclusive (setting one nullifies the other)
- Null = no target mode

### 5. Component Replacement by Category
- Adding a component replaces existing one in same category
- Prevents multiple CPUs, GPUs, etc. in a build
- Automatically releases old reservations

## Performance Considerations

### Optimizations
- ✅ Computed properties use efficient DB relationships
- ✅ Single query to fetch build with all components
- ✅ No N+1 queries (uses SQLAlchemy relationships)
- ✅ Indexes on foreign keys (automatic in SQLite)

### Scalability
- ✅ Calculations scale linearly with component count
- ✅ Typical builds have 8-12 components (fast)
- ✅ No heavy computations or aggregations
- ✅ Database operations are transactional

## Future Enhancements (Not Implemented)

These were not in scope but could be added:

1. **Batch Component Operations**: Add multiple components in one request
2. **Build Templates**: Save/load component lists
3. **Profit Optimization Suggestions**: AI-powered component recommendations
4. **Historical Profit Tracking**: Track actual vs projected profit
5. **Build Comparison**: Side-by-side comparison of multiple builds
6. **Component Substitution**: Suggest alternative parts
7. **Market Price Integration**: Auto-update MSRP from APIs
8. **Build Sharing**: Share builds with other users

## Conclusion

The PC Planner module is a complete, production-ready implementation that satisfies all specified requirements. It provides:

- ✅ Per-component margin visibility
- ✅ Target profit mode with real-time analysis
- ✅ Inventory-aware component selection
- ✅ Soft reservation system
- ✅ Hybrid inventory/external builds
- ✅ Safe, auditable, deterministic operations
- ✅ Comprehensive API with 13 endpoints
- ✅ Full documentation and testing

The planner empowers PC flippers to:
- Optimize margins per part
- Plan builds without owning all components
- Reserve parts safely while planning
- Understand exactly why a build is or isn't profitable

All code follows the existing codebase patterns, uses the established tech stack (FastAPI, SQLAlchemy), and integrates seamlessly with the existing inventory and builder systems.
