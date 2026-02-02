/**
 * Bundle Acquisition & Cost Allocation Modal
 * Handles multi-component purchase allocation with weighted percentages
 */

let bundleLineItems = [];
let bundlePresets = {};
let bundleProducts = [];
let nextLineItemId = 1;

// Initialize: Load presets and products
async function initBundleModal() {
    try {
        // Load presets
        const presetsRes = await fetch('/api/inventory/bundles/presets');
        bundlePresets = await presetsRes.json();
        
        // Load products
        const productsRes = await fetch('/api/inventory/products/all');
        bundleProducts = await productsRes.json();
    } catch (error) {
        console.error('Error initializing bundle modal:', error);
    }
}

// Open bundle modal
function openBundleModal() {
    initBundleModal();
    bundleLineItems = [];
    nextLineItemId = 1;
    
    // Reset form
    document.getElementById('bundleTotalPrice').value = '';
    document.getElementById('bundleVendor').value = '';
    document.getElementById('bundlePurchaseDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('bundleNotes').value = '';
    document.getElementById('allocationPreset').value = '';
    
    // Show modal
    document.getElementById('bundleModal').style.display = 'flex';
    
    renderLineItems();
    updateAllocationSummary();
}

// Close bundle modal
function closeBundleModal() {
    document.getElementById('bundleModal').style.display = 'none';
}

// Line item structure
function createLineItem() {
    return {
        id: nextLineItemId++,
        category: '',
        product_id: null,
        product_name: '',
        quantity: 1,
        weight: 0,
        allocated_cost: 0,
        is_locked: false,
        condition: 'new',
        vendor_sku: '',
        serial_number: '',
        notes: ''
    };
}

// Add new line item
function addBundleLineItem() {
    bundleLineItems.push(createLineItem());
    renderLineItems();
    updateAllocationSummary();
}

// Remove line item
function removeBundleLineItem(itemId) {
    bundleLineItems = bundleLineItems.filter(item => item.id !== itemId);
    renderLineItems();
    recalculateAllocations();
}

// Toggle lock on line item
function toggleLock(itemId) {
    const item = bundleLineItems.find(i => i.id === itemId);
    if (item) {
        item.is_locked = !item.is_locked;
        renderLineItems();
        recalculateAllocations();
    }
}

// Update line item field
function updateLineItem(itemId, field, value) {
    const item = bundleLineItems.find(i => i.id === itemId);
    if (item) {
        if (field === 'quantity') {
            item.quantity = parseInt(value) || 1;
        } else if (field === 'weight') {
            item.weight = parseFloat(value) || 0;
        } else if (field === 'allocated_cost') {
            item.allocated_cost = parseFloat(value) || 0;
            // Auto-lock when manually edited
            item.is_locked = true;
        } else if (field === 'category') {
            item.category = value;
        } else if (field === 'product_id') {
            item.product_id = value ? parseInt(value) : null;
            if (value === '__new__') {
                const name = prompt('Enter product name:');
                if (name) {
                    item.product_name = name;
                    item.product_id = null;
                }
            } else if (value) {
                const product = bundleProducts.find(p => p.id === parseInt(value));
                if (product) {
                    item.product_name = product.name;
                    item.category = product.category;
                }
            }
        } else {
            item[field] = value;
        }
        
        renderLineItems();
        if (field === 'weight' || field === 'quantity') {
            recalculateAllocations();
        } else {
            updateAllocationSummary();
        }
    }
}

// Apply preset weights
function applyPreset() {
    const presetKey = document.getElementById('allocationPreset').value;
    if (!presetKey || !bundlePresets[presetKey]) {
        return;
    }
    
    const preset = bundlePresets[presetKey];
    const weights = preset.weights;
    
    // Apply weights to existing items based on category
    bundleLineItems.forEach(item => {
        if (item.category && weights[item.category]) {
            if (!item.is_locked) {
                item.weight = weights[item.category];
            }
        }
    });
    
    renderLineItems();
    recalculateAllocations();
}

// Allocation Engine - Core logic
function recalculateAllocations() {
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    
    if (bundleTotal <= 0 || bundleLineItems.length === 0) {
        updateAllocationSummary();
        return;
    }
    
    // Separate locked and unlocked items
    const lockedItems = bundleLineItems.filter(item => item.is_locked);
    const unlockedItems = bundleLineItems.filter(item => !item.is_locked);
    
    // Calculate locked total
    const lockedTotal = lockedItems.reduce((sum, item) => 
        sum + (item.allocated_cost * item.quantity), 0);
    
    // Remaining amount for unlocked items
    const remainingAmount = bundleTotal - lockedTotal;
    
    // Calculate total weight of unlocked items
    const totalWeight = unlockedItems.reduce((sum, item) => sum + item.weight, 0);
    
    if (totalWeight > 0 && remainingAmount > 0) {
        // Distribute proportionally with deterministic rounding
        let distributedTotal = 0;
        
        unlockedItems.forEach((item, index) => {
            if (index === unlockedItems.length - 1) {
                // Last item gets remainder to ensure exact match
                const remaining = remainingAmount - distributedTotal;
                item.allocated_cost = remaining / item.quantity;
            } else {
                const itemTotal = (item.weight / totalWeight) * remainingAmount;
                item.allocated_cost = itemTotal / item.quantity;
                distributedTotal += itemTotal;
            }
        });
    } else if (totalWeight === 0 && unlockedItems.length > 0 && remainingAmount > 0) {
        // Distribute evenly if no weights
        const perItem = remainingAmount / unlockedItems.length;
        unlockedItems.forEach((item, index) => {
            if (index === unlockedItems.length - 1) {
                const remaining = remainingAmount - (perItem * (unlockedItems.length - 1));
                item.allocated_cost = remaining / item.quantity;
            } else {
                item.allocated_cost = perItem / item.quantity;
            }
        });
    }
    
    renderLineItems();
    updateAllocationSummary();
}

// Render line items table
function renderLineItems() {
    const tbody = document.getElementById('bundleLineItemsBody');
    const emptyMsg = document.getElementById('emptyLineItemsMessage');
    
    if (bundleLineItems.length === 0) {
        tbody.innerHTML = '';
        emptyMsg.style.display = 'block';
        return;
    }
    
    emptyMsg.style.display = 'none';
    
    tbody.innerHTML = bundleLineItems.map(item => {
        const lockIcon = item.is_locked ? '🔒' : '🔓';
        const lockTitle = item.is_locked ? 'Locked (manual allocation)' : 'Unlocked (auto-calculated)';
        
        return `
            <tr data-item-id="${item.id}">
                <td>
                    <select class="bundle-input" onchange="updateLineItem(${item.id}, 'category', this.value)">
                        <option value="">Select...</option>
                        <option value="CPU" ${item.category === 'CPU' ? 'selected' : ''}>CPU</option>
                        <option value="GPU" ${item.category === 'GPU' ? 'selected' : ''}>GPU</option>
                        <option value="Motherboard" ${item.category === 'Motherboard' ? 'selected' : ''}>Motherboard</option>
                        <option value="RAM" ${item.category === 'RAM' ? 'selected' : ''}>RAM</option>
                        <option value="Storage" ${item.category === 'Storage' ? 'selected' : ''}>Storage</option>
                        <option value="PSU" ${item.category === 'PSU' ? 'selected' : ''}>PSU</option>
                        <option value="Case" ${item.category === 'Case' ? 'selected' : ''}>Case</option>
                        <option value="Cooling" ${item.category === 'Cooling' ? 'selected' : ''}>Cooling</option>
                        <option value="Extras" ${item.category === 'Extras' ? 'selected' : ''}>Extras</option>
                    </select>
                </td>
                <td>
                    <select class="bundle-input" onchange="updateLineItem(${item.id}, 'product_id', this.value)">
                        <option value="">Select product...</option>
                        <option value="__new__">+ Create new product</option>
                        ${bundleProducts.map(p => 
                            `<option value="${p.id}" ${item.product_id === p.id ? 'selected' : ''}>${p.name} (${p.category})</option>`
                        ).join('')}
                    </select>
                    ${item.product_name && !item.product_id ? `<small>${item.product_name}</small>` : ''}
                </td>
                <td>
                    <input type="number" class="bundle-input" min="1" value="${item.quantity}" 
                           onchange="updateLineItem(${item.id}, 'quantity', this.value)">
                </td>
                <td>
                    <input type="number" class="bundle-input" step="0.1" min="0" value="${item.weight.toFixed(1)}" 
                           onchange="updateLineItem(${item.id}, 'weight', this.value)" 
                           ${item.is_locked ? 'disabled' : ''}>
                </td>
                <td>
                    <input type="number" class="bundle-input" step="0.01" min="0" value="${item.allocated_cost.toFixed(2)}" 
                           onchange="updateLineItem(${item.id}, 'allocated_cost', this.value)">
                </td>
                <td style="text-align: center;">
                    <button type="button" class="lock-btn" onclick="toggleLock(${item.id})" title="${lockTitle}">
                        ${lockIcon}
                    </button>
                </td>
                <td>
                    <button type="button" class="action-btn delete-btn" onclick="removeBundleLineItem(${item.id})">Remove</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Update allocation summary
function updateAllocationSummary() {
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    const totalAllocated = bundleLineItems.reduce((sum, item) => 
        sum + (item.allocated_cost * item.quantity), 0);
    const remaining = bundleTotal - totalAllocated;
    
    document.getElementById('summaryBundleTotal').textContent = `$${bundleTotal.toFixed(2)}`;
    document.getElementById('summaryTotalAllocated').textContent = `$${totalAllocated.toFixed(2)}`;
    document.getElementById('summaryRemaining').textContent = `$${remaining.toFixed(2)}`;
    
    // Validation
    const validation = validateBundle();
    const statusEl = document.getElementById('validationStatus');
    const submitBtn = document.getElementById('bundleSubmitBtn');
    const warningEl = document.getElementById('allocationWarning');
    
    if (validation.valid) {
        statusEl.textContent = '✓ READY';
        statusEl.className = 'summary-status valid';
        submitBtn.disabled = false;
        warningEl.style.display = 'block';
    } else {
        statusEl.textContent = validation.message;
        statusEl.className = 'summary-status invalid';
        submitBtn.disabled = true;
        warningEl.style.display = 'none';
    }
}

// Validation Logic
function validateBundle() {
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    const vendor = document.getElementById('bundleVendor').value.trim();
    const purchaseDate = document.getElementById('bundlePurchaseDate').value;
    
    // Check required fields
    if (!bundleTotal || bundleTotal <= 0) {
        return { valid: false, message: "Bundle total required" };
    }
    if (!vendor) {
        return { valid: false, message: "Vendor required" };
    }
    if (!purchaseDate) {
        return { valid: false, message: "Purchase date required" };
    }
    
    // Check line items
    if (bundleLineItems.length === 0) {
        return { valid: false, message: "Add at least one component" };
    }
    
    // Validate each line item
    for (const item of bundleLineItems) {
        if (!item.category) {
            return { valid: false, message: "All components need category" };
        }
        if (!item.product_id && !item.product_name) {
            return { valid: false, message: "All components need product" };
        }
        if (item.quantity < 1) {
            return { valid: false, message: "Quantity must be at least 1" };
        }
        if (item.allocated_cost < 0) {
            return { valid: false, message: "Allocated cost cannot be negative" };
        }
    }
    
    // Check allocation match
    const totalAllocated = bundleLineItems.reduce((sum, item) => 
        sum + (item.allocated_cost * item.quantity), 0);
    
    const difference = Math.abs(totalAllocated - bundleTotal);
    if (difference > 0.01) {
        return { valid: false, message: `Mismatch: $${difference.toFixed(2)}` };
    }
    
    return { valid: true, message: "Ready to submit" };
}

// Submit bundle
async function submitBundle() {
    const validation = validateBundle();
    if (!validation.valid) {
        alert('Validation failed: ' + validation.message);
        return;
    }
    
    // Confirmation dialog
    if (!confirm('These costs are estimated allocations and may not reflect resale value. Continue?')) {
        return;
    }
    
    const payload = {
        total_price: parseFloat(document.getElementById('bundleTotalPrice').value),
        vendor: document.getElementById('bundleVendor').value.trim(),
        purchase_date: document.getElementById('bundlePurchaseDate').value + 'T00:00:00',
        notes: document.getElementById('bundleNotes').value.trim() || null,
        components: bundleLineItems.map(item => ({
            product_id: item.product_id,
            product_name: item.product_name || null,
            category: item.category,
            quantity: item.quantity,
            allocation_weight: item.weight,
            allocated_cost: item.allocated_cost,
            is_locked: item.is_locked,
            condition: item.condition,
            vendor_sku: item.vendor_sku || null,
            serial_number: item.serial_number || null,
            notes: item.notes || null,
        }))
    };
    
    try {
        const response = await fetch('/api/inventory/bundles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create bundle');
        }
        
        const result = await response.json();
        alert(`Bundle created successfully! ${result.lot_ids.length} components added to inventory.`);
        closeBundleModal();
        
        // Refresh inventory table if available
        if (typeof loadComponents === 'function') {
            loadComponents();
        }
    } catch (error) {
        alert('Error creating bundle: ' + error.message);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBundleModal);
} else {
    initBundleModal();
}
