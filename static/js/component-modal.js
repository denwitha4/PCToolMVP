// Modal functions (reusable across pages)
function openModal(category = "") {
    document.getElementById('modalTitle').textContent = 'Add Component';
    document.getElementById('componentName').value = '';
    document.getElementById('componentCost').value = '';
    document.getElementById('componentMSRP').value = '';
    const categorySelect = document.getElementById('componentCategory'); // ✓ This name
    const categoryFormGroup = document.getElementById('categoryFormGroup');

    if (category !== '') {
        // Hide the entire form group (label + dropdown)
        categoryFormGroup.style.display = 'none';
        categorySelect.value = category; // ✓ Fixed - use categorySelect
        console.log('Category set to:', categorySelect.value);
    } else {
        // Show the form group
        categoryFormGroup.style.display = 'block';
        categorySelect.value = '';
    }

    editingId = null;
    document.getElementById('componentModal').classList.add('active');
}

function closeModal() {
    document.getElementById('componentModal').classList.remove('active');
}

function editComponent(id) {
    const component = components.find(c => c.id === id);
    if (!component) return;

    document.getElementById('modalTitle').textContent = 'Edit Component';
    document.getElementById('componentName').value = component.name;
    document.getElementById('componentCategory').value = component.category;
    document.getElementById('componentCost').value = component.cost;
    document.getElementById('componentMSRP').value = component.msrp || '';
    editingId = id;
    document.getElementById('componentModal').classList.add('active');
}

async function saveComponent() {
    const name = document.getElementById('componentName').value;
    const category = document.getElementById('componentCategory').value;
    const cost = parseFloat(document.getElementById('componentCost').value);
    const msrp = parseFloat(document.getElementById('componentMSRP').value) || null;

    if (!name || !category || !cost) {
        alert('Please fill in all required fields');
        return;
    }

    const componentData = { name, category, cost_per_unit: cost, msrp };

    try {
        let response;
        if (editingId) {
            response = await fetch(`/api/inventory/components/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(componentData)
            });
        } else {
            response = await fetch('/api/inventory/components', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(componentData)
            });
        }

        if (response.ok) {
            await loadComponents(); // This will need to be called from the page
            closeModal();
        } else {
            const error = await response.json();
            alert('Error saving component: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving component:', error);
        alert('Error saving component');
    }
}

async function deleteComponent(id) {
    if (!confirm('Are you sure you want to delete this component?')) return;

    try {
        const response = await fetch(`/api/inventory/components/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadComponents(); // This will need to be called from the page
        } else {
            const error = await response.json();
            alert('Error deleting component: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting component:', error);
        alert('Error deleting component');
    }
}