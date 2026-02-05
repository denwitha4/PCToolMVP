let editingComponentId = null;
let products = [];

function openModal(category) {
    document.getElementById('modalTitle').textContent = 'Add Component';
    editingComponentId = null;
    document.getElementById('productSelect').value = '';
    document.getElementById('productSelect').disabled = false;
    document.getElementById('newProductFields').style.display = 'none';
    document.getElementById('productName').value = '';
    document.getElementById('productCategory').value = category || '';
    document.getElementById('productMSRP').value = '';
    document.getElementById('lotVendor').value = '';
    document.getElementById('lotUnitCost').value = '';
    document.getElementById('lotTotalCost').value = '';
    document.getElementById('lotQuantity').value = '1';
    document.getElementById('lotCondition').value = 'new';
    document.getElementById('lotSalesTax').value = '0';
    document.getElementById('lotShippingCost').value = '0';
    document.getElementById('lotFees').value = '0';
    document.getElementById('lotVendorSku').value = '';
    document.getElementById('lotSerialNumber').value = '';
    document.getElementById('lotStorageLocation').value = '';
    document.getElementById('lotNotes').value = '';
    loadProductsForModal();
    wireCostQuantitySyncOnce();
    if (typeof updateCostQuantityUI === 'function') updateCostQuantityUI();
    document.getElementById('componentModal').classList.add('active');
}

function closeModal() {
    document.getElementById('componentModal').classList.remove('active');
}

async function loadProductsForModal() {
    try {
        const res = await fetch('/api/inventory/products/all');
        products = await res.json();
        const select = document.getElementById('productSelect');
        const firstOpt = select.options[0];
        const secondOpt = select.options[1];
        select.innerHTML = '';
        select.appendChild(firstOpt);
        select.appendChild(secondOpt);
        products.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name + (p.category ? ' (' + p.category + ')' : '');
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Error loading products', err);
    }
}

document.getElementById('productSelect').addEventListener('change', function () {
    const newFields = document.getElementById('newProductFields');
    newFields.style.display = this.value === '__new__' ? 'block' : 'none';
});

function updateCostQuantityUI() {
    console.log('updateCostQuantityUI');
    const qty = parseInt(document.getElementById('lotQuantity').value, 10) || 1;
    const unitInput = document.getElementById('lotUnitCost');
    const totalInput = document.getElementById('lotTotalCost');
    const totalGroup = document.getElementById('lotTotalCostGroup');
    const unitLabel = document.getElementById('lotUnitCostLabel');

    const row = document.getElementById('costQuantityRow');
    if (qty > 1) {
        totalGroup.style.display = 'block';
        if (row) row.classList.add('has-total');
        unitLabel.textContent = 'Unit Cost';
        syncTotalFromUnitCost();
    } else {
        totalGroup.style.display = 'none';
        if (row) row.classList.remove('has-total');
        unitLabel.textContent = 'Cost';
        const unitVal = parseFloat(unitInput.value);
        if (!isNaN(unitVal) && unitVal >= 0) totalInput.value = unitVal.toFixed(2);
    }
}

function syncUnitCostFromTotal() {
    const qty = parseInt(document.getElementById('lotQuantity').value, 10) || 1;
    if (qty <= 0) return;
    const totalInput = document.getElementById('lotTotalCost');
    const unitInput = document.getElementById('lotUnitCost');
    const total = parseFloat(totalInput.value);
    if (!isNaN(total) && total >= 0) {
        unitInput.value = (total / qty).toFixed(2);
    }
}

function syncTotalFromUnitCost() {
    const qty = parseInt(document.getElementById('lotQuantity').value, 10) || 1;
    const unitInput = document.getElementById('lotUnitCost');
    const totalInput = document.getElementById('lotTotalCost');
    const unit = parseFloat(unitInput.value);
    if (!isNaN(unit) && unit >= 0) {
        totalInput.value = (unit * qty).toFixed(2);
    }
}

let costQuantitySyncWired = false;

function wireCostQuantitySyncOnce() {
    if (costQuantitySyncWired) return;
    const qtyEl = document.getElementById('lotQuantity');
    const unitEl = document.getElementById('lotUnitCost');
    const totalEl = document.getElementById('lotTotalCost');
    if (!qtyEl || !unitEl || !totalEl) return;
    costQuantitySyncWired = true;
    qtyEl.addEventListener('input', function () {
        updateCostQuantityUI();
        syncTotalFromUnitCost();
    });
    qtyEl.addEventListener('change', function () {
        updateCostQuantityUI();
        syncTotalFromUnitCost();
    });
    unitEl.addEventListener('input', syncTotalFromUnitCost);
    totalEl.addEventListener('input', syncUnitCostFromTotal);
}

async function saveComponent() {
    const productSelect = document.getElementById('productSelect').value;
    const isNewProduct = productSelect === '__new__';
    let productId = productSelect && productSelect !== '__new__' ? parseInt(productSelect, 10) : null;

    if (isNewProduct) {
        const name = document.getElementById('productName').value.trim();
        const category = document.getElementById('productCategory').value;
        const msrp = document.getElementById('productMSRP').value;
        if (!name || !category) {
            alert('Please enter product name and category for new product.');
            return;
        }
        try {
            const res = await fetch('/api/inventory/products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    category,
                    msrp: msrp ? parseFloat(msrp) : null,
                }),
            });
            if (!res.ok) throw new Error(await res.text());
            const product = await res.json();
            productId = product.id;
        } catch (err) {
            alert('Failed to create product: ' + err.message);
            return;
        }
    }

    if (!productId) {
        alert('Please select or create a product.');
        return;
    }

    const unitCost = parseFloat(document.getElementById('lotUnitCost').value);
    const quantity = parseInt(document.getElementById('lotQuantity').value, 10) || 1;
    if (isNaN(unitCost) || unitCost < 0) {
        alert('Please enter a valid unit cost.');
        return;
    }

    const componentPayload = {
        product_id: productId,
        vendor: document.getElementById('lotVendor').value.trim() || 'Unknown',
        unit_cost: unitCost,
        quantity_on_hand: quantity,
        condition: document.getElementById('lotCondition').value,
        sales_tax: parseFloat(document.getElementById('lotSalesTax').value) || 0,
        shipping_cost: parseFloat(document.getElementById('lotShippingCost').value) || 0,
        fees: parseFloat(document.getElementById('lotFees').value) || 0,
        vendor_sku: document.getElementById('lotVendorSku').value.trim() || null,
        serial_number: document.getElementById('lotSerialNumber').value.trim() || null,
        storage_location: document.getElementById('lotStorageLocation').value.trim() || null,
        notes: document.getElementById('lotNotes').value.trim() || null,
    };

    try {
        if (editingComponentId) {
            const res = await fetch('/api/inventory/components/' + editingComponentId, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vendor: componentPayload.vendor,
                    unit_cost: componentPayload.unit_cost,
                    quantity_on_hand: componentPayload.quantity_on_hand,
                    sales_tax: componentPayload.sales_tax,
                    shipping_cost: componentPayload.shipping_cost,
                    fees: componentPayload.fees,
                    condition: componentPayload.condition,
                    vendor_sku: componentPayload.vendor_sku,
                    serial_number: componentPayload.serial_number,
                    storage_location: componentPayload.storage_location,
                    notes: componentPayload.notes,
                }),
            });
            if (!res.ok) throw new Error(await res.json().then(d => d.detail || JSON.stringify(d)));
        } else {
            const res = await fetch('/api/inventory/components', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(componentPayload),
            });
            if (!res.ok) throw new Error(await res.json().then(d => d.detail || JSON.stringify(d)));
        }
        closeModal();
        window.dispatchEvent(new CustomEvent('componentSaved'));
    } catch (err) {
        alert('Error saving component: ' + (err.message || err));
    }
}

async function editComponent(componentId) {
    try {
        const res = await fetch('/api/inventory/components/' + componentId);
        if (!res.ok) throw new Error('Component not found');
        const component = await res.json();
        editingComponentId = componentId;
        document.getElementById('modalTitle').textContent = 'Edit Component';
        await loadProductsForModal();
        document.getElementById('productSelect').value = String(component.product_id);
        document.getElementById('productSelect').disabled = true;
        document.getElementById('newProductFields').style.display = 'none';
        document.getElementById('lotVendor').value = component.vendor || '';
        const qty = component.quantity_on_hand ?? 1;
        const unitCost = component.unit_cost ?? 0;
        document.getElementById('lotUnitCost').value = unitCost !== '' ? unitCost : '';
        document.getElementById('lotTotalCost').value = (qty > 1 && unitCost !== '') ? (parseFloat(unitCost) * qty).toFixed(2) : (unitCost !== '' ? unitCost : '');
        document.getElementById('lotQuantity').value = qty;
        document.getElementById('lotCondition').value = component.condition || 'new';
        document.getElementById('lotSalesTax').value = component.sales_tax ?? 0;
        document.getElementById('lotShippingCost').value = component.shipping_cost ?? 0;
        document.getElementById('lotFees').value = component.fees ?? 0;
        document.getElementById('lotVendorSku').value = component.vendor_sku || '';
        document.getElementById('lotSerialNumber').value = component.serial_number || '';
        document.getElementById('lotStorageLocation').value = component.storage_location || '';
        document.getElementById('lotNotes').value = component.notes || '';
        wireCostQuantitySyncOnce();
        if (typeof updateCostQuantityUI === 'function') updateCostQuantityUI();
        document.getElementById('componentModal').classList.add('active');
    } catch (err) {
        alert('Error loading component: ' + err.message);
    }
}

async function loadComponents(category, selectedId) {
    if (typeof loadComponents !== 'undefined' && window.loadComponents) {
        window.loadComponents();
    }
}

function deleteComponent(id) {
    if (!confirm('Soft delete this component? It will be hidden from the list.')) return;
    fetch('/api/inventory/components/soft-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_ids: [id] }),
    }).then(r => {
        if (r.ok) window.dispatchEvent(new CustomEvent('componentSaved'));
        else r.json().then(d => alert('Error: ' + (d.detail || 'Unknown')));
    }).catch(() => alert('Error deleting component'));
}

// Legacy saveLot for backward compatibility
function saveLot() {
    saveComponent();
}

// Legacy editLot for backward compatibility
function editLot(id) {
    editComponent(id);
}
