// Override native alert to prevent pywebview deadlock on macOS
window.alert = function(msg) {
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
    overlay.style.zIndex = '99999';
    overlay.style.display = 'flex';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.backdropFilter = 'blur(5px)';
    
    overlay.innerHTML = `
        <div class="glass-panel" style="padding: 30px; text-align: center; min-width: 300px; animation: modalFadeIn 0.3s ease;">
            <p style="margin-bottom: 30px; font-size: 1.1rem; color: #fff;">${msg}</p>
            <button onclick="this.closest('.glass-panel').parentElement.remove()" class="btn btn-primary" style="width: 100%;">Aceptar</button>
        </div>
    `;
    document.body.appendChild(overlay);
};

document.addEventListener('DOMContentLoaded', () => {
    // Navigation highlighting
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            navItems.forEach(nav => nav.classList.remove('active'));
            e.currentTarget.classList.add('active');

            const target = e.currentTarget.getAttribute('data-target');

            document.getElementById('page-title').innerText = e.currentTarget.querySelector('span').innerText;

            // Fetch the new view
            document.getElementById('content-area').innerHTML = '<div style="text-align:center; padding: 50px;"><i class="fa-solid fa-spinner fa-spin fa-3x text-primary"></i><p style="margin-top:20px; color:var(--text-muted);">Cargando...</p></div>';
            
            fetch(`/view/${target}`)
              .then(res => {
                  if(!res.ok) throw new Error("Vista no encontrada");
                  return res.text();
              })
              .then(html => {
                  document.getElementById('content-area').innerHTML = html;
                  const scripts = document.getElementById('content-area').querySelectorAll('script');
                  scripts.forEach(oldScript => {
                      const newScript = document.createElement('script');
                      Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                      newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                      oldScript.parentNode.replaceChild(newScript, oldScript);
                  });
                  loadViewData(target);
              })
              .catch(err => {
                  document.getElementById('content-area').innerHTML = `<div style="text-align:center; color:var(--danger); padding:50px;">Error: ${err.message}</div>`;
              });
        });
    });

    const activeNav = document.querySelector('.nav-item.active');
    if (activeNav) activeNav.click();
});

function loadViewData(view, page) {
    if (view === 'clients') {
        page = page || 1;
        const search = document.getElementById('search-clients') ? document.getElementById('search-clients').value : '';
        const status = document.getElementById('filter-clients') ? document.getElementById('filter-clients').value : 'all';
        
        let url = `/api/clients?page=${page}&per_page=50`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status !== 'all') url += `&status=${status}`;
        
        fetch(url).then(r => r.json()).then(data => {
            window.clientsData = data.clients;
            window.clientsPage = data.page;
            window.clientsPages = data.pages;
            window.clientsTotal = data.total;
            if(window.renderClientsTable) {
                window.renderClientsTable();
            }
        });
    } else if (view === 'inventory') {
        fetch('/api/products').then(r => r.json()).then(data => {
            const tbody = document.getElementById('inventory-table-body');
            tbody.innerHTML = '';
            if(data.length === 0) tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 20px;">No hay productos registrados.</td></tr>';
            data.forEach(p => {
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid var(--glass-border);">
                        <td style="padding: 15px 20px;">${p.name}</td>
                        <td style="padding: 15px 20px;">$${p.price.toFixed(2)}</td>
                        <td style="padding: 15px 20px; text-align: right;">
                            <button onclick="editProduct(${p.id}, '${p.name}', ${p.price})" class="btn-icon" style="display:inline-flex; width:35px; height:35px;"><i class="fa-solid fa-pen text-primary"></i></button>
                            <button onclick="deleteItem('products', ${p.id}, 'inventory')" class="btn-icon" style="display:inline-flex; width:35px; height:35px; margin-left: 5px;"><i class="fa-solid fa-trash text-danger"></i></button>
                        </td>
                    </tr>
                `;
            });
        });
    } else if (view === 'plans') {
        fetch('/api/plans').then(r => r.json()).then(data => {
            const grid = document.getElementById('plans-grid');
            grid.innerHTML = '';
            if(data.length === 0) grid.innerHTML = '<p style="text-align:center; grid-column:1/-1;">No hay planes registrados.</p>';
            data.forEach(p => {
                grid.innerHTML += `
                    <div class="action-card glass-panel" style="align-items: flex-start; text-align: left; position: relative;">
                        <div style="position:absolute; top:15px; right:15px; display:flex; gap:5px;">
                            <button onclick="editPlan(${p.id}, '${p.name}', ${p.duration_days}, ${p.price})" style="background:transparent; border:none; font-size: 1rem; color:var(--text-muted); cursor:pointer;"><i class="fa-solid fa-pen"></i></button>
                            <button onclick="deleteItem('plans', ${p.id}, 'plans')" style="background:transparent; border:none; font-size: 1rem; color:var(--danger); cursor:pointer;"><i class="fa-solid fa-trash"></i></button>
                        </div>
                        <h3 style="font-size:1.2rem; margin-bottom:5px;">${p.name}</h3>
                        <p style="color:var(--text-muted); font-size:0.9rem;">Duración: ${p.duration_days} días</p>
                        <p style="font-size:1.5rem; font-weight:bold; color:var(--success); margin-top:10px;">$${p.price.toFixed(2)}</p>
                    </div>
                `;
            });
        });
    } else if (view === 'employees') {
        fetch('/api/employees').then(r => r.json()).then(data => {
            const tbody = document.getElementById('employees-table-body');
            tbody.innerHTML = '';
            if(data.length === 0) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">No hay empleados registrados.</td></tr>';
            data.forEach(e => {
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid var(--glass-border);">
                        <td style="padding: 15px 20px;">${e.id}</td>
                        <td style="padding: 15px 20px;">${e.name}</td>
                        <td style="padding: 15px 20px;">${e.username}</td>
                        <td style="padding: 15px 20px;">${e.role === 'admin' ? 'Administrador' : 'Usuario'}</td>
                        <td style="padding: 15px 20px; text-align: right;">
                            <button onclick="editEmployee(${e.id}, '${e.name}', '${e.username}', '${e.role}')" class="btn-icon" style="display:inline-flex; width:35px; height:35px;"><i class="fa-solid fa-pen text-primary"></i></button>
                            <button onclick="deleteItem('employees', ${e.id}, 'employees')" class="btn-icon" style="display:inline-flex; width:35px; height:35px; margin-left: 5px;"><i class="fa-solid fa-trash text-danger"></i></button>
                        </td>
                    </tr>
                `;
            });
        });
    }
}

window.deleteItem = function(api_route, id, viewToReload) {
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
    overlay.style.zIndex = '99999';
    overlay.style.display = 'flex';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.backdropFilter = 'blur(5px)';
    
    overlay.innerHTML = `
        <div class="glass-panel" style="padding: 30px; text-align: center; max-width: 400px; animation: modalFadeIn 0.3s ease;">
            <h3 style="margin-bottom: 15px; color: var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Confirmar Eliminación</h3>
            <p style="margin-bottom: 25px; color: var(--text-muted);">¿Estás seguro de que deseas eliminar este registro? Esta acción no se puede deshacer.</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button id="btn-cancel-del" class="btn btn-secondary">Cancelar</button>
                <button id="btn-confirm-del" class="btn btn-primary" style="background: var(--danger); border-color: var(--danger);">Eliminar</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    
    document.getElementById('btn-cancel-del').onclick = () => {
        overlay.remove();
    };
    
    document.getElementById('btn-confirm-del').onclick = async () => {
        overlay.remove();
        try {
            const res = await fetch(`/api/${api_route}/${id}`, { method: 'DELETE' });
            if(res.ok) {
                loadViewData(viewToReload);
            } else {
                alert('Error al eliminar');
            }
        } catch(err) {
            alert('Error de conexión');
        }
    };
}
