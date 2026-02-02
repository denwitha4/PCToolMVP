# PC Planner - Quick Start Guide

## What Was Built

I've implemented a comprehensive PC Planner module that enables profit-aware, inventory-aware PC build planning for your PC flipping application.

## Files Created

1. **`routes/planner.py`** (600+ lines)
   - Complete planner API with 13 endpoints
   - Per-component margin calculations
   - Target profit analysis
   - Inventory-aware selection
   - Soft reservation system

2. **`PLANNER_README.md`**
   - Complete user documentation
   - API endpoint reference
   - Usage examples and workflows

3. **`PLANNER_IMPLEMENTATION.md`**
   - Technical implementation details
   - Requirements mapping
   - Design decisions

4. **`test_planner.py`**
   - Test script to verify functionality

## Files Modified

1. **`database.py`**
   - Enhanced `Build` model with target profit fields
   - Enhanced `BuildComponent` model with external component support
   - Added migration function for new fields

2. **`main.py`**
   - Added planner router to application

## Core Features Implemented

### ✅ 1. Per-Component Margin Visibility
- Component cost (inventory or manual)
- Component MSRP
- Profit margin ($ and %)
- Contribution to total cost (%)

### ✅ 2. Target Profit Mode
- Set target as fixed $ or %
- Real-time calculation of max allowable cost
- Status: meets/under/over_budget
- Identifies problematic components

### ✅ 3. Inventory-Aware Selection
- Distinguishes inventory vs external parts
- Shows available quantities
- Supports hybrid builds
- Tracks sourcing separately

### ✅ 4. Soft Reservation System
- Reserve inventory for specific builds
- Reduces available inventory
- Does NOT mark as sold
- Fully reversible
- Enables concurrent build planning

## API Endpoints (13 Total)

### Build Management
- `POST /api/planner/builds` - Create build
- `GET /api/planner/builds` - List all builds
- `GET /api/planner/builds/{id}` - Get build details
- `PUT /api/planner/builds/{id}` - Update build
- `DELETE /api/planner/builds/{id}` - Delete build

### Component Management
- `POST /api/planner/builds/{id}/components` - Add component
- `PUT /api/planner/builds/{id}/components/{cid}` - Update component
- `DELETE /api/planner/builds/{id}/components/{cid}` - Remove component

### Analysis & Inventory
- `GET /api/planner/builds/{id}/target-profit-analysis` - Analyze profit
- `GET /api/planner/builds/{id}/reservations` - View reservations
- `GET /api/planner/inventory-available` - Browse inventory

### Reservations
- `POST /api/planner/builds/{id}/reserve` - Soft reserve
- `DELETE /api/planner/builds/{id}/reserve/{lot_id}` - Release reservation

## Quick Usage Example

### 1. Create a Build with Target Profit
```bash
curl -X POST http://localhost:8000/api/planner/builds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming PC Build 1",
    "target_profit_percentage": 30
  }'
```

### 2. Browse Available Inventory
```bash
curl http://localhost:8000/api/planner/inventory-available?category=GPU
```

### 3. Add Component (Inventory-Backed)
```bash
curl -X POST http://localhost:8000/api/planner/builds/1/components \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "lot_id": 10,
    "quantity": 1,
    "cost_at_time": 399.99,
    "is_external": false
  }'
```

### 4. Add External Component
```bash
curl -X POST http://localhost:8000/api/planner/builds/1/components \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 2,
    "lot_id": null,
    "quantity": 1,
    "cost_at_time": 149.99,
    "is_external": true
  }'
```

### 5. Get Target Profit Analysis
```bash
curl http://localhost:8000/api/planner/builds/1/target-profit-analysis
```

### 6. Get Build with All Metrics
```bash
curl http://localhost:8000/api/planner/builds/1
```

## Response Example

```json
{
  "id": 1,
  "name": "Gaming PC Build 1",
  "total_cost": 1299.93,
  "total_msrp": 1899.93,
  "projected_profit": 600.00,
  "projected_margin_percentage": 31.58,
  "target_profit_percentage": 30,
  "meets_target_profit": true,
  "max_allowable_cost": 1329.95,
  "target_status": "meets",
  "components": [
    {
      "product_name": "RTX 4070",
      "category": "GPU",
      "total_cost": 599.99,
      "total_msrp": 799.99,
      "profit_absolute": 200.00,
      "profit_margin_percentage": 25.0,
      "cost_contribution_percentage": 46.15,
      "is_inventory_backed": true,
      "inventory_available": 3
    }
  ]
}
```

## Testing

Run the test script:
```bash
python test_planner.py
```

Or test manually using curl/Postman with the endpoints above.

## Key Design Features

### Safety
- ✅ Never auto-buys or modifies parts
- ✅ Soft reservations only (reversible)
- ✅ Inventory never goes negative
- ✅ External parts don't affect inventory

### Flexibility
- ✅ Mix inventory and external parts
- ✅ Switch components between sources
- ✅ Plan multiple builds concurrently
- ✅ Target profit optional

### Accuracy
- ✅ All metrics calculated dynamically
- ✅ Real-time updates
- ✅ Deterministic calculations
- ✅ Full audit trail

## Database Changes

New fields automatically added via migration:

**builds table:**
- `target_profit_amount`
- `target_profit_percentage`
- `created_at`
- `updated_at`

**build_components table:**
- `is_external`
- `quantity_from_inventory`
- `quantity_external`
- `external_cost`

## Next Steps

1. **Test the API**: Use `test_planner.py` or curl
2. **Review Documentation**: Check `PLANNER_README.md` for full details
3. **Build UI**: Create frontend interfaces for the planner
4. **Integrate**: Connect with existing builder and sales modules

## Support

All planner logic is self-contained in `routes/planner.py`. The module:
- Does NOT modify inventory system
- Reuses existing `Build` and `BuildComponent` tables
- Compatible with existing `/api/builder` routes
- Follows all project coding patterns

## Key Success Metrics

✅ **All Requirements Met**:
- Per-component margin visibility
- Target profit mode
- Inventory-aware selection
- Soft reservation system

✅ **Production Ready**:
- 13 API endpoints
- Full error handling
- Authentication integrated
- Database migrations included

✅ **Well Documented**:
- User guide (README)
- Implementation details
- Test scripts
- Quick start (this file)

## Server Status

The server should restart automatically and include the planner routes. Check for:
```
INFO:     Application startup complete.
```

The planner is now available at `/api/planner/*` endpoints.
