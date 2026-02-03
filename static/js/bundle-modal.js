/**
 * Bundle Acquisition & Cost Allocation Modal
 */

let bundleLineItems = [];
let bundlePresets = {};
let bundleProducts = [];
let nextLineItemId = 1;
const PRODUCT_PICKER_MAX_RESULTS = 15;
let productPickerCloseTimer = null;

async function initBundleModal() {
    try {
        const presetsRes = await fetch('/api/inventory/bundles/presets');
        bundlePresets = await presetsRes.json();
        const productsRes = await fetch('/api/inventory/products/all');
        bundleProducts = await productsRes.json();
    } catch (error) {
        console.error('Error initializing bundle modal:', error);
    }
}

function openBundleModal() {
    initBundleModal();
    bundleLineItems = [];
    nextLineItemId = 1;
    document.getElementById('bundleTotalPrice').value = '';
    document.getElementById('bundleVendor').value = '';
    document.getElementById('bundlePurchaseDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('bundleNotes').value = '';
    document.getElementById('allocationPreset').value = '';
    document.getElementById('bundleModal').style.display = 'flex';
    renderLineItems();
    updateAllocationSummary();
}

function closeBundleModal() {
    document.getElementById('bundleModal').style.display = 'none';
}

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

function getProductDisplayName(item) {
    if (item.product_id) {
        const p = bundleProducts.find(pr => pr.id === item.product_id);
        return p ? p.name : (item.product_name || '');
    }
    return item.product_name || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openProductPicker(itemId) {
    const input = document.getElementById('productSearch-' + itemId);
    if (!input) return;
    filterProductPicker(itemId, input.value);
}

function filterProductPicker(itemId, searchText) {
    const dropdown = document.getElementById('productPickerDropdown-' + itemId);
    if (!dropdown) return;
    const term = (searchText || '').trim().toLowerCase();
    const item = bundleLineItems.find(i => i.id === itemId);
    const category = item ? item.category : '';
    const hasCategory = category && category !== '' && category !== 'Select...';
    let pool = bundleProducts;
    if (hasCategory) {
        pool = bundleProducts.filter(p => p.category === category);
    }
    let filtered = term
        ? pool.filter(p => {
            const matchName = p.name.toLowerCase().includes(term);
            const matchCat = p.category && p.category.toLowerCase().includes(term);
            return matchName || matchCat;
        })
        : pool.slice(0, PRODUCT_PICKER_MAX_RESULTS);
    if (term && filtered.length > 0) {
        filtered = filtered.sort((a, b) => {
            const aStarts = a.name.toLowerCase().startsWith(term) ? 1 : 0;
            const bStarts = b.name.toLowerCase().startsWith(term) ? 1 : 0;
            if (bStarts !== aStarts) return bStarts - aStarts;
            return a.name.localeCompare(b.name);
        });
    }
    const slice = filtered.slice(0, PRODUCT_PICKER_MAX_RESULTS);
    let html = slice.map(p => {
        const label = p.category ? p.name + ' (' + p.category + ')' : p.name;
        return '<div class="product-picker-option" data-product-id="' + p.id + '" onclick="selectBundleProduct(' + itemId + ',' + p.id + '); event.stopPropagation();">' + escapeHtml(label) + '</div>';
    }).join('');
    html += '<div class="product-picker-option product-picker-new" onclick="selectNewProduct(' + itemId + '); event.stopPropagation();">+ New Component</div>';
    dropdown.innerHTML = html;
    dropdown.classList.add('open');
}

function closeProductPicker(itemId) {
    const dropdown = document.getElementById('productPickerDropdown-' + itemId);
    if (dropdown) dropdown.classList.remove('open');
}

function scheduleCloseProductPicker(itemId) {
    if (productPickerCloseTimer) clearTimeout(productPickerCloseTimer);
    productPickerCloseTimer = setTimeout(function () { closeProductPicker(itemId); }, 200);
}

function selectBundleProduct(itemId, productId) {
    const item = bundleLineItems.find(i => i.id === itemId);
    const product = bundleProducts.find(p => p.id === productId);
    if (!item || !product) return;
    item.product_id = productId;
    item.product_name = product.name;
    item.category = product.category;
    const input = document.getElementById('productSearch-' + itemId);
    if (input) input.value = product.name;
    closeProductPicker(itemId);
    hideNewProductInline(itemId);
    updateAllocationSummary();
}

async function selectNewProduct(itemId) {
    const item = bundleLineItems.find(i => i.id === itemId);
    const input = document.getElementById('productSearch-' + itemId);
    const searchText = input ? input.value.trim() : '';
    closeProductPicker(itemId);
    if (searchText) {
        try {
            const res = await fetch('/api/inventory/products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: searchText,
                    category: item ? item.category : 'Extras',
                    msrp: null
                })
            });
            if (!res.ok) throw new Error(await res.text());
            const product = await res.json();
            bundleProducts.push(product);
            item.product_id = product.id;
            item.product_name = product.name;
            item.category = product.category;
            if (input) input.value = product.name;
            updateAllocationSummary();
        } catch (err) {
            console.error('Failed to create product:', err);
            alert('Failed to create product: ' + err.message);
        }
    } else {
        showNewProductInline(itemId);
    }
}

function showNewProductInline(itemId) {
    const wrap = document.getElementById('productPickerNewWrap-' + itemId);
    const input = document.getElementById('productNewName-' + itemId);
    if (wrap) wrap.style.display = 'block';
    if (input) {
        input.value = '';
        input.focus();
    }
}

function hideNewProductInline(itemId) {
    const wrap = document.getElementById('productPickerNewWrap-' + itemId);
    const input = document.getElementById('productNewName-' + itemId);
    if (wrap) wrap.style.display = 'none';
    if (input) input.value = '';
}

async function createNewProductFromInline(itemId) {
    const item = bundleLineItems.find(i => i.id === itemId);
    const input = document.getElementById('productNewName-' + itemId);
    const mainInput = document.getElementById('productSearch-' + itemId);
    const name = input ? input.value.trim() : '';
    if (!name) {
        hideNewProductInline(itemId);
        return;
    }
    try {
        const res = await fetch('/api/inventory/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                category: item ? item.category : 'Extras',
                msrp: null
            })
        });
        if (!res.ok) throw new Error(await res.text());
        const product = await res.json();
        bundleProducts.push(product);
        item.product_id = product.id;
        item.product_name = product.name;
        item.category = product.category;
        if (mainInput) mainInput.value = product.name;
        hideNewProductInline(itemId);
        updateAllocationSummary();
    } catch (err) {
        console.error('Failed to create product:', err);
        alert('Failed to create product: ' + err.message);
    }
}

function addBundleLineItem() {
    bundleLineItems.push(createLineItem());
    renderLineItems();
    updateAllocationSummary();
}

function removeBundleLineItem(itemId) {
    bundleLineItems = bundleLineItems.filter(item => item.id !== itemId);
    renderLineItems();
    recalculateAllocations();
}

function toggleLock(itemId) {
    const item = bundleLineItems.find(i => i.id === itemId);
    if (item) {
        item.is_locked = !item.is_locked;
        renderLineItems();
        recalculateAllocations();
    }
}

function updateLineItem(itemId, field, value) {
    const item = bundleLineItems.find(i => i.id === itemId);
    if (!item) return;
    if (field === 'quantity') item.quantity = parseInt(value) || 1;
    else if (field === 'weight') item.weight = parseFloat(value) || 0;
    else if (field === 'allocated_cost') {
        item.allocated_cost = parseFloat(value) || 0;
        item.is_locked = true;
    } else if (field === 'category') item.category = value;
    else if (field === 'product_id') {
        item.product_id = value ? parseInt(value) : null;
        if (value) {
            const product = bundleProducts.find(p => p.id === parseInt(value));
            if (product) {
                item.product_name = product.name;
                item.category = product.category;
            }
        }
    } else if (field === 'product_name') {
        item.product_name = value;
        item.product_id = null;
    } else {
        item[field] = value;
    }
    renderLineItems();
    if (field === 'weight' || field === 'quantity') recalculateAllocations();
    else updateAllocationSummary();
}

function applyPreset() {
    const presetKey = document.getElementById('allocationPreset').value;
    if (!presetKey || !bundlePresets[presetKey]) return;
    const preset = bundlePresets[presetKey];
    bundleLineItems = [];
    if (preset.auto_populate && preset.components && preset.components.length > 0) {
        preset.components.forEach(function (comp) {
            const lineItem = createLineItem();
            lineItem.category = comp.category;
            lineItem.quantity = comp.quantity;
            lineItem.weight = comp.weight;
            lineItem.is_locked = false;
            bundleLineItems.push(lineItem);
        });
    }
    renderLineItems();
    recalculateAllocations();
}

function recalculateAllocations() {
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    if (bundleTotal <= 0 || bundleLineItems.length === 0) {
        updateAllocationSummary();
        return;
    }
    const lockedItems = bundleLineItems.filter(item => item.is_locked);
    const unlockedItems = bundleLineItems.filter(item => !item.is_locked);
    const lockedTotal = lockedItems.reduce((sum, item) => sum + (item.allocated_cost * item.quantity), 0);
    const remainingAmount = bundleTotal - lockedTotal;
    const totalWeight = unlockedItems.reduce((sum, item) => sum + item.weight, 0);
    if (totalWeight > 0 && remainingAmount > 0) {
        let distributedTotal = 0;
        unlockedItems.forEach(function (item, index) {
            if (index === unlockedItems.length - 1) {
                const remaining = remainingAmount - distributedTotal;
                item.allocated_cost = remaining / item.quantity;
            } else {
                const itemTotal = (item.weight / totalWeight) * remainingAmount;
                item.allocated_cost = itemTotal / item.quantity;
                distributedTotal += itemTotal;
            }
        });
    } else if (totalWeight === 0 && unlockedItems.length > 0 && remainingAmount > 0) {
        const perItem = remainingAmount / unlockedItems.length;
        unlockedItems.forEach(function (item, index) {
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

function renderLineItems() {
    const tbody = document.getElementById('bundleLineItemsBody');
    const emptyMsg = document.getElementById('emptyLineItemsMessage');
    if (bundleLineItems.length === 0) {
        tbody.innerHTML = '';
        emptyMsg.style.display = 'block';
        return;
    }
    emptyMsg.style.display = 'none';
    tbody.innerHTML = bundleLineItems.map(function (item) {
        const lockIcon = item.is_locked ? '\uD83D\uDD12' : '\uD83D\uDD13';
        const lockTitle = item.is_locked ? 'Locked' : 'Unlocked';
        const displayName = escapeHtml(getProductDisplayName(item));
        return '<tr data-item-id="' + item.id + '">' +
            '<td><select class="bundle-input" onchange="updateLineItem(' + item.id + ', \'category\', this.value)">' +
            '<option value="">Select...</option>' +
            '<option value="CPU"' + (item.category === 'CPU' ? ' selected' : '') + '>CPU</option>' +
            '<option value="GPU"' + (item.category === 'GPU' ? ' selected' : '') + '>GPU</option>' +
            '<option value="Motherboard"' + (item.category === 'Motherboard' ? ' selected' : '') + '>Motherboard</option>' +
            '<option value="RAM"' + (item.category === 'RAM' ? ' selected' : '') + '>RAM</option>' +
            '<option value="Storage"' + (item.category === 'Storage' ? ' selected' : '') + '>Storage</option>' +
            '<option value="PSU"' + (item.category === 'PSU' ? ' selected' : '') + '>PSU</option>' +
            '<option value="Case"' + (item.category === 'Case' ? ' selected' : '') + '>Case</option>' +
            '<option value="Cooling"' + (item.category === 'Cooling' ? ' selected' : '') + '>Cooling</option>' +
            '<option value="Extras"' + (item.category === 'Extras' ? ' selected' : '') + '>Extras</option>' +
            '</select></td>' +
            '<td class="product-picker-cell">' +
            '<div class="product-picker-wrap">' +
            '<input type="text" class="bundle-input product-search-input" id="productSearch-' + item.id + '" data-item-id="' + item.id + '" placeholder="Search products..." value="' + displayName + '" autocomplete="off" onfocus="openProductPicker(' + item.id + ')" oninput="filterProductPicker(' + item.id + ', this.value)" onblur="scheduleCloseProductPicker(' + item.id + ')">' +
            '<div class="product-picker-dropdown" id="productPickerDropdown-' + item.id + '" data-item-id="' + item.id + '"></div>' +
            '<div class="product-picker-new-wrap" id="productPickerNewWrap-' + item.id + '" style="display: none;">' +
            '<input type="text" class="bundle-input" id="productNewName-' + item.id + '" placeholder="New product name" onkeydown="if(event.key===\'Enter\') createNewProductFromInline(' + item.id + ')" onblur="createNewProductFromInline(' + item.id + ')">' +
            '</div></div></td>' +
            '<td><input type="number" class="bundle-input" min="1" value="' + item.quantity + '" onchange="updateLineItem(' + item.id + ', \'quantity\', this.value)"></td>' +
            '<td><input type="number" class="bundle-input" step="0.1" min="0" value="' + item.weight.toFixed(1) + '" onchange="updateLineItem(' + item.id + ', \'weight\', this.value)" ' + (item.is_locked ? 'disabled' : '') + '></td>' +
            '<td><input type="number" class="bundle-input" step="0.01" min="0" value="' + item.allocated_cost.toFixed(2) + '" onchange="updateLineItem(' + item.id + ', \'allocated_cost\', this.value)"></td>' +
            '<td style="text-align: center;"><button type="button" class="lock-btn" onclick="toggleLock(' + item.id + ')" title="' + lockTitle + '">' + lockIcon + '</button></td>' +
            '<td><button type="button" class="action-btn delete-btn" onclick="removeBundleLineItem(' + item.id + ')">Remove</button></td>' +
            '</tr>';
    }).join('');
}

function updateAllocationSummary() {
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    const totalAllocated = bundleLineItems.reduce((sum, item) => sum + (item.allocated_cost * item.quantity), 0);
    const remaining = bundleTotal - totalAllocated;
    document.getElementById('summaryBundleTotal').textContent = '$' + bundleTotal.toFixed(2);
    document.getElementById('summaryTotalAllocated').textContent = '$' + totalAllocated.toFixed(2);
    document.getElementById('summaryRemaining').textContent = '$' + remaining.toFixed(2);
    const validation = validateBundle();
    const statusEl = document.getElementById('validationStatus');
    const submitBtn = document.getElementById('bundleSubmitBtn');
    const warningEl = document.getElementById('allocationWarning');
    if (validation.valid) {
        statusEl.textContent = 'READY';
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

function validateBundle() {
    const presetSelected = document.getElementById('allocationPreset').value;
    if (!presetSelected) return { valid: false, message: 'Please select a bundle type' };
    const bundleTotal = parseFloat(document.getElementById('bundleTotalPrice').value) || 0;
    const vendor = document.getElementById('bundleVendor').value.trim();
    const purchaseDate = document.getElementById('bundlePurchaseDate').value;
    if (!bundleTotal || bundleTotal <= 0) return { valid: false, message: 'Bundle total required' };
    if (!vendor) return { valid: false, message: 'Vendor required' };
    if (!purchaseDate) return { valid: false, message: 'Purchase date required' };
    if (bundleLineItems.length === 0) return { valid: false, message: 'Add at least one component' };
    for (const item of bundleLineItems) {
        if (!item.category) return { valid: false, message: 'All components need category' };
        if (!item.product_id && !item.product_name) return { valid: false, message: 'All components need product' };
        if (item.quantity < 1) return { valid: false, message: 'Quantity must be at least 1' };
        if (item.allocated_cost < 0) return { valid: false, message: 'Allocated cost cannot be negative' };
    }
    const totalAllocated = bundleLineItems.reduce((sum, item) => sum + (item.allocated_cost * item.quantity), 0);
    const difference = Math.abs(totalAllocated - bundleTotal);
    if (difference > 0.01) return { valid: false, message: 'Mismatch: $' + difference.toFixed(2) };
    return { valid: true, message: 'Ready to submit' };
}

async function submitBundle() {
    const validation = validateBundle();
    if (!validation.valid) {
        alert('Validation failed: ' + validation.message);
        return;
    }
    if (!confirm('These costs are estimated allocations and may not reflect resale value. Continue?')) return;
    const payload = {
        total_price: parseFloat(document.getElementById('bundleTotalPrice').value),
        vendor: document.getElementById('bundleVendor').value.trim(),
        purchase_date: document.getElementById('bundlePurchaseDate').value + 'T00:00:00',
        notes: document.getElementById('bundleNotes').value.trim() || null,
        components: bundleLineItems.map(function (item) {
            return {
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
                notes: item.notes || null
            };
        })
    };
    try {
        const response = await fetch('/api/inventory/bundles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create bundle');
        }
        const result = await response.json();
        alert('Bundle created successfully! ' + result.lot_ids.length + ' components added to inventory.');
        closeBundleModal();
        if (typeof loadComponents === 'function') loadComponents();
    } catch (error) {
        alert('Error creating bundle: ' + error.message);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBundleModal);
} else {
    initBundleModal();
}
