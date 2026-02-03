# Plan: Multiple Components Per Category in Builds

Allow users to add more than one component of the same category to a single build (e.g. two GPUs, two or more storage drives). Currently every build has at most one component per category; the planner **replaces** the existing component when you add another in the same category.

---

## 1. Current State

| Layer | Behavior |
|-------|----------|
| **DB** | `BuildComponent` has no unique constraint on `(build_id, category)`. Category comes from `Product`. Multiple rows per build with same category are already allowed. |
| **Backend** | **Add component** (POST) in `routes/planner.py` (lines 414–427): if a component of the same category exists, it **releases** its reservation, **deletes** that row, then adds the new one → effectively one per category. |
| **Build metrics** | `Build.total_cost`, `total_msrp`, `projected_profit`, etc. sum over **all** `build_components` → no change needed. |
| **Frontend** | `buildComponents` is keyed by category: `buildComponents[category] = singleComponent`. Table has one row per category. Add/remove use category. |

So the only hard “one per category” rule is in the **planner add-component** logic and the **edit UI** data shape and rendering.

---

## 2. Backend Changes

**File: `routes/planner.py`**

- **Add component (POST)**  
  - Remove the “replace existing same category” block (query for `existing` by category, release reservation, `db.delete(existing)`).  
  - Always **add** a new `BuildComponent`; do not delete any existing component by category.  
  - Keep reservation logic as-is (reserve the lot for this new component).

- **List components**  
  - No change. `calculate_build_metrics(build)` already returns all `build.build_components`; the list can contain multiple components with the same category.

- **Update / Remove component**  
  - No change. Both operate by `component_id`; they already support multiple components per category.

**Optional (later):**

- Add a `slot_order` (integer) or `display_order` on `BuildComponent` and sort by it in list responses if you want stable “GPU 1 / GPU 2” ordering. For MVP, ordering by `BuildComponent.id` or `created_at` is enough.

---

## 3. Frontend Data Model (edit.html)

**Current:** `buildComponents[category]` = single object → one row per category.

**Target:** Support multiple components per category. Two equivalent options:

- **Option A – Array per category**  
  `buildComponents[category] = [ { buildComponentId, productId, lotId, name, cost, msrp, ... }, ... ]`  
  - Pros: Easy to “add another GPU” (push to array).  
  - Cons: Need a stable way to identify “which row” when removing (use `buildComponentId`).

- **Option B – Flat slots**  
  `buildSlots = [ { id, category, buildComponentId, name, cost, ... }, ... ]`  
  - Pros: One loop for rendering; “Add another GPU” = append slot with category GPU.  
  - Cons: Deriving “required categories” for progress (e.g. “has at least one CPU, one GPU, …”) requires scanning.

**Recommendation:** Option A (array per category). Keep `componentCategories` for the list of categories; each category can have 0, 1, or many components. When loading from API, group `components` by `category` into arrays.

---

## 4. Frontend UI Behavior

- **Table rows**  
  - One **row per component**, not per category.  
  - Same category can appear multiple times (e.g. “GPU” + “3060 12GB”, then “GPU” + “RTX 4070”).  
  - First column can show category name (and optionally “GPU 1”, “GPU 2” or “Storage 1”, “Storage 2” for clarity).  
  - Each row has its own dropdown (by category) and Remove button; Remove uses `buildComponentId`.

- **“Add component”**  
  - **Option 1:** One “+ Add [Category]” button per category; clicking opens the same category dropdown and adds a **new** row (new slot) when user selects a product. No replacement.  
  - **Option 2:** Below the table, “+ Add component” opens a modal or dropdown to pick category, then product.  
  - Recommendation: Option 1 for MVP — keep “+ Choose GPU” / “+ Add another GPU” in the same column so adding a second GPU is obvious.

- **Dropdown**  
  - Each row’s dropdown still filters inventory by that row’s category.  
  - Selecting a product in that dropdown **adds** a new component (new row) for that category, or **replaces** only if we later introduce “replace this slot” (e.g. when there’s exactly one row for that category and we want backward compatibility). For a clean multi-component model: **always add** from dropdown; “Replace” can be “Remove this row + add new one” if needed.

- **Remove**  
  - Each row’s Remove button calls `removeComponent(buildComponentId)` (or same API with component id). Already supported by `DELETE /api/planner/builds/{id}/components/{component_id}`.

- **Progress**  
  - Today: “X of 8 components” (one per category).  
  - New: Define “required” categories (e.g. CPU, GPU, Motherboard, RAM, Storage, PSU, Case, Cooling = 8). Progress can be “X of 8 required categories filled” (at least one component in each), and optionally “+ N optional” (extra GPU/storage).  
  - Progress bar can stay 0–100% based on “required categories filled” so a build with 2 GPUs and 2 storage still shows 8/8 when all required have at least one.

---

## 5. Load and Render Flow (edit.html)

1. **Load build**  
   `GET /api/planner/builds/{id}` → `currentBuild` with `components[]` (each has `id`, `category`, `product_name`, etc.).

2. **Build local state**  
   - `buildComponents = {}`  
   - For each `componentCategories` category, `buildComponents[cat] = []`.  
   - For each `currentBuild.components`, push to `buildComponents[bc.category]`.

3. **Render table**  
   - Iterate over categories; for each category iterate over `buildComponents[category]` and emit one row per component.  
   - For categories with 0 components, emit one “empty” row with “+ Choose [Category]” (and optional “+ Add another [Category]” when there’s already at least one).

4. **Row identity**  
   - Use `buildComponentId` for remove and for dropdown id (e.g. `dropdown-${category}-${buildComponentId}`) so multiple rows for the same category don’t share one dropdown.

5. **Add component**  
   - `selectComponent(category, componentId)` (or new `addComponent(category, lotId/productId, ...)`) → POST add component; on success reload build and re-render (step 1–3). No “replace by category” in UI.

---

## 6. Optional Enhancements (Later)

- **Max per category**  
  - Config or UI: e.g. “Max 2 GPUs”, “Max 4 storage”. Backend can enforce on POST; frontend can hide “Add another GPU” when limit reached.

- **Slot order**  
  - Add `slot_order` (or use `display_order`) on `BuildComponent` and sort in API so “GPU 1” / “GPU 2” order is stable after reordering (if you add drag-and-drop later).

- **Required vs optional categories**  
  - Progress and validation could treat e.g. CPU, Motherboard, RAM, Storage, PSU, Case, Cooling as required and GPU as optional (or vice versa). For MVP, “at least one per category in componentCategories” is enough.

---

## 7. Implementation Order

1. **Backend**  
   In `routes/planner.py`, remove the “existing same category” block in the add-component endpoint so adding a component always inserts a new row and never deletes by category.

2. **Frontend – data**  
   In `edit.html`, change `loadBuildComponents()` to fill `buildComponents[category]` as an **array** (group `bcData` by `bc.category`).

3. **Frontend – render**  
   Change `renderComponentCards()` to loop over categories and then over `buildComponents[category]`, rendering one table row per component; empty state = one row per category with “+ Choose [Category]”.

4. **Frontend – add**  
   Ensure “Add another [Category]” is available when a category already has at least one component (extra row or button that opens same dropdown). `selectComponent(category, componentId)` should call POST add (no replace).

5. **Frontend – remove**  
   Pass `buildComponentId` (and optionally category) to `removeComponent`; keep calling existing DELETE by component id.

6. **Frontend – progress**  
   Update `updateProgress()` to “required categories with at least one component” (e.g. 8 categories) so multiple GPUs/storage don’t break the progress logic.

7. **Manual test**  
   Add build with 2 GPUs and 2 storage; check summary totals, remove one, add again, and confirm reservations and build metrics.

---

## 8. Summary

| Item | Action |
|------|--------|
| DB | No schema change. |
| Planner add | Stop replace-by-category; always add new BuildComponent. |
| Planner list/update/delete | No change. |
| Edit UI data | `buildComponents[category]` = array of components. |
| Edit UI table | One row per component; multiple rows per category. |
| Add component | Always add (new row); “+ Add another [Category]” when category already has ≥1. |
| Remove | By `buildComponentId` (already supported). |
| Progress | “X of 8 required categories” (at least one component per category). |

This plan keeps the existing API and DB and only relaxes the one-per-category rule in the add endpoint and the edit UI, so users can add multiple drives or multiple GPUs (or any category) per build.
