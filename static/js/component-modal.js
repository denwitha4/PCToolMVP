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
        document.getElementById('lotUnitCost').value = component.unit_cost ?? '';
        document.getElementById('lotQuantity').value = component.quantity_on_hand ?? 1;
        document.getElementById('lotCondition').value = component.condition || 'new';
        document.getElementById('lotSalesTax').value = component.sales_tax ?? 0;
        document.getElementById('lotShippingCost').value = component.shipping_cost ?? 0;
        document.getElementById('lotFees').value = component.fees ?? 0;
        document.getElementById('lotVendorSku').value = component.vendor_sku || '';
        document.getElementById('lotSerialNumber').value = component.serial_number || '';
        document.getElementById('lotStorageLocation').value = component.storage_location || '';
        document.getElementById('lotNotes').value = component.notes || '';
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
