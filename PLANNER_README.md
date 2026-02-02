# PC Planner Module - Documentation

## Overview

The PC Planner is a profit-aware, inventory-aware decision engine that helps PC flippers optimize margins, plan builds, and manage inventory reservations. It provides detailed per-component analytics and supports both inventory-backed and external (planned purchase) components.

## Core Features

### 1. Per-Component Margin Visibility

Each component in a build exposes:
- **Component cost** (from inventory or manual input)
- **Component MSRP** (from product catalog)
- **Component profit margin** (absolute $ and %)
- **Component contribution to total build cost** (%)

Works for both inventory-backed and external components.

### 2. Target Profit Mode

Define a target profit as either:
- **Fixed dollar amount** (e.g., $500 profit)
- **Percentage margin** (e.g., 30% margin)

The planner calculates:
- Maximum allowable total build cost
- Whether the current build meets, is under, or is over target
- Which components are causing budget overruns

### 3. Inventory-Aware Component Selection

The planner distinguishes between:
- **Parts that exist in inventory** (shows available quantity, highlights ownership)
- **Parts that do NOT exist** (marked as external/planned purchase)

Supports hybrid builds with mixed inventory and external parts.

### 4. Soft Reservation Mode

From the planner, you can:
- **Soft-reserve** inventory parts for a specific build
- **Reduces available inventory** without marking as sold
- **Reversible** - can be released or modified
- Tracks which lots are reserved and quantity per lot

Enables planning multiple builds simultaneously without conflicts.

## API Endpoints

### Build Management

#### Create a Build
```
POST /api/planner/builds
{
  "name": "Gaming PC Build 1",
  "target_profit_amount": 500,  // Optional: fixed dollar target
  "target_profit_percentage": 30  // Optional: percentage target (use one or the other)
}
```

#### Get All Builds
```
GET /api/planner/builds
```

Returns all builds with basic metrics for the authenticated user.

#### Get Build Details
```
GET /api/planner/builds/{build_id}
```

Returns detailed build plan with:
- All components with per-component metrics
- Total cost, MSRP, projected profit
- Target profit analysis
- Inventory status for each component

#### Update Build
```
PUT /api/planner/builds/{build_id}
{
  "name": "Updated Build Name",
  "target_profit_amount": 600,
  "target_profit_percentage": null
}
```

#### Delete Build
```
DELETE /api/planner/builds/{build_id}
```

Automatically releases all inventory reservations.

### Component Management

#### Add Component to Build
```
POST /api/planner/builds/{build_id}/components
{
  "product_id": 123,
  "lot_id": 456,  // Optional: null for external components
  "quantity": 1,
  "cost_at_time": 299.99,
  "is_external": false  // true for planned purchases
}
```

**Behavior:**
- Replaces existing component of the same category
- Automatically soft-reserves inventory if `lot_id` provided and `is_external` is false
- Releases previous reservation if replacing

#### Update Component
```
PUT /api/planner/builds/{build_id}/components/{component_id}
{
  "quantity": 2,
  "cost_at_time": 279.99,
  "is_external": false,
  "lot_id": 456
}
```

**Behavior:**
- Adjusts reservations if quantity changes
- Switches between inventory and external sourcing
- Updates cost without affecting inventory

#### Remove Component
```
DELETE /api/planner/builds/{build_id}/components/{component_id}
```

Automatically releases any reservations.

### Inventory & Reservations

#### Get Available Inventory
```
GET /api/planner/inventory-available?category=GPU
```

Returns all available inventory lots with:
- Product details (name, category, MSRP)
- Inventory status (available, reserved, on-hand)
- Cost information
- Vendor and condition

#### Manual Soft Reserve
```
POST /api/planner/builds/{build_id}/reserve
{
  "lot_id": 456,
  "quantity": 2
}
```

#### Release Reservation
```
DELETE /api/planner/builds/{build_id}/reserve/{lot_id}?quantity=2
```

#### Get Build Reservations
```
GET /api/planner/builds/{build_id}/reservations
```

Returns all inventory reservations for the build.

### Target Profit Analysis

#### Get Target Profit Analysis
```
GET /api/planner/builds/{build_id}/target-profit-analysis
```

Returns detailed analysis:
- Current profit vs target
- Whether target is met
- Maximum allowable cost
- Cost variance
- Problematic components (if over budget)

## Data Models

### Build Entity
```python
{
  "id": 1,
  "name": "Gaming PC Build 1",
  "status": 1,  // PLANNING, BUILDING, LISTING, SELLING, SOLD
  "total_cost": 1200.00,
  "total_msrp": 1800.00,
  "projected_profit": 600.00,
  "projected_margin_percentage": 33.33,
  "target_profit_amount": 500.00,
  "target_profit_percentage": null,
  "meets_target_profit": true,
  "max_allowable_cost": 1300.00,
  "target_mode": "active",
  "target_status": "meets",
  "cost_variance": 100.00,
  "component_count": 8
}
```

### Component Entity (within Build)
```python
{
  "id": 1,
  "product_id": 123,
  "product_name": "RTX 4070",
  "category": "GPU",
  "quantity": 1,
  "unit_cost": 599.99,
  "total_cost": 599.99,
  "unit_msrp": 799.99,
  "total_msrp": 799.99,
  "profit_absolute": 200.00,
  "profit_margin_percentage": 25.0,
  "cost_contribution_percentage": 50.0,
  "is_inventory_backed": true,
  "is_external": false,
  "lot_id": 456,
  "inventory_available": 3,
  "inventory_reserved": 1,
  "has_sufficient_inventory": true,
  "vendor": "Newegg",
  "condition": "new"
}
```

## Calculation Rules

### Cost Calculations
- **Total Build Cost**: Sum of all component costs (unit_cost × quantity)
- **Total MSRP**: Sum of all component MSRPs (msrp × quantity)
- **Projected Profit**: Total MSRP - Total Build Cost
- **Margin %**: (Projected Profit / Total MSRP) × 100

### Target Profit Calculations
- **Fixed Dollar Target**: Max Cost = Total MSRP - Target Profit Amount
- **Percentage Target**: Max Cost = Total MSRP × (1 - Target % / 100)

### Per-Component Metrics
- **Component Profit**: (MSRP × Quantity) - (Cost × Quantity)
- **Component Margin %**: (Component Profit / Component MSRP) × 100
- **Cost Contribution %**: (Component Cost / Total Build Cost) × 100

## Inventory Management

### Reservation States
- **Available**: `quantity_available = quantity_on_hand - quantity_reserved`
- **Reserved**: Reduces available inventory, tracked per build
- **Status**: Changes to `RESERVED` when any quantity is reserved

### Reservation Rules
1. Cannot reserve more than available quantity
2. Reservations are per lot (not per product)
3. Multiple builds can reserve from different lots of the same product
4. Reservations must be released before quantity goes negative
5. External components do NOT affect inventory

## Usage Workflow

### Planning a New Build

1. **Create Build**
   ```
   POST /api/planner/builds
   {
     "name": "High-End Gaming PC",
     "target_profit_percentage": 35
   }
   ```

2. **Check Available Inventory**
   ```
   GET /api/planner/inventory-available?category=CPU
   ```

3. **Add Components**
   ```
   POST /api/planner/builds/{build_id}/components
   {
     "product_id": 1,
     "lot_id": 10,
     "quantity": 1,
     "cost_at_time": 399.99,
     "is_external": false
   }
   ```

4. **Review Metrics**
   ```
   GET /api/planner/builds/{build_id}
   ```

5. **Analyze Target Profit**
   ```
   GET /api/planner/builds/{build_id}/target-profit-analysis
   ```

### Mixed Inventory + External Build

1. Add inventory-backed components:
   ```
   POST /api/planner/builds/{build_id}/components
   {
     "product_id": 1,
     "lot_id": 10,
     "quantity": 1,
     "cost_at_time": 399.99,
     "is_external": false  // From inventory
   }
   ```

2. Add external (planned purchase) components:
   ```
   POST /api/planner/builds/{build_id}/components
   {
     "product_id": 2,
     "lot_id": null,
     "quantity": 1,
     "cost_at_time": 149.99,
     "is_external": true  // Will purchase later
   }
   ```

### Switching Component Source

Convert from external to inventory:
```
PUT /api/planner/builds/{build_id}/components/{component_id}
{
  "is_external": false,
  "lot_id": 15
}
```

Convert from inventory to external:
```
PUT /api/planner/builds/{build_id}/components/{component_id}
{
  "is_external": true,
  "lot_id": null
}
```

## Target Profit Modes

### Fixed Dollar Target
```json
{
  "target_profit_amount": 500,
  "target_profit_percentage": null
}
```
- Requires exactly $500 profit
- Max cost = Total MSRP - $500

### Percentage Target
```json
{
  "target_profit_amount": null,
  "target_profit_percentage": 30
}
```
- Requires 30% margin
- Max cost = Total MSRP × 0.70

### Target Status Values
- **`meets`**: Current build meets or exceeds target
- **`under_target`**: Build is profitable but below target
- **`over_budget`**: Build cost exceeds max allowable cost
- **`null`**: No target set

## Safety & Constraints

### Hard Rules
1. ✅ Planner NEVER auto-buys or auto-adjusts parts
2. ✅ Planner NEVER hard-reserves or sells inventory
3. ✅ Inventory quantities NEVER go negative
4. ✅ External components NEVER affect inventory counts
5. ✅ Planner can be used concurrently across multiple builds
6. ✅ All calculations are deterministic and auditable

### Soft Reservations
- Reduce available inventory
- Do NOT mark items as sold
- Can be released or modified
- Track which lots are reserved per build
- Automatically released when build is deleted

## Integration Points

### With Inventory System
- Reads product catalog (name, category, MSRP)
- Reads inventory lots (cost, quantity, availability)
- Manages soft reservations (quantity_reserved)
- Does NOT mutate inventory quantities directly

### With Build System
- Reuses `Build` and `BuildComponent` tables
- Adds planner-specific fields (target profit, external flags)
- Compatible with existing builder routes
- Shares build status enum

## Example Response: Full Build Metrics

```json
{
  "id": 1,
  "name": "Gaming PC Build 1",
  "status": 1,
  "total_cost": 1299.93,
  "total_msrp": 1899.93,
  "projected_profit": 600.00,
  "projected_margin_percentage": 31.58,
  "target_profit_amount": null,
  "target_profit_percentage": 30,
  "meets_target_profit": true,
  "max_allowable_cost": 1329.95,
  "target_mode": "active",
  "target_status": "meets",
  "cost_variance": 30.02,
  "component_count": 8,
  "components": [
    {
      "id": 1,
      "product_id": 1,
      "product_name": "Intel i7-13700K",
      "category": "CPU",
      "quantity": 1,
      "unit_cost": 399.99,
      "total_cost": 399.99,
      "unit_msrp": 549.99,
      "total_msrp": 549.99,
      "profit_absolute": 150.00,
      "profit_margin_percentage": 27.27,
      "cost_contribution_percentage": 30.77,
      "is_inventory_backed": true,
      "is_external": false,
      "lot_id": 10,
      "inventory_available": 2,
      "inventory_reserved": 1,
      "has_sufficient_inventory": true,
      "vendor": "Amazon",
      "condition": "new"
    },
    {
      "id": 2,
      "product_name": "Corsair RM850x PSU",
      "category": "PSU",
      "is_external": true,
      "inventory_available": 0,
      "vendor": "External",
      "condition": "N/A"
    }
  ]
}
```

## Testing the Planner

### Test Scenarios

1. **Create a build with target profit**
2. **Add all components from inventory**
3. **Verify reservations reduce available inventory**
4. **Check target profit analysis shows "meets"**
5. **Add expensive component, verify "over_budget" status**
6. **Remove expensive component, back to "meets"**
7. **Switch component from inventory to external**
8. **Delete build, verify all reservations released**

## Notes

- All monetary values are in USD (Float)
- Quantities are integers
- Calculations are performed dynamically (not persisted)
- User authentication required for all endpoints
- All endpoints scoped to authenticated user
