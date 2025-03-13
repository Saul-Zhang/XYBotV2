document.addEventListener('DOMContentLoaded', function() {
    // 页面切换
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            
            // 更新导航栏激活状态
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // 显示对应页面
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(`page-${page}`).classList.add('active');
            
            // 加载页面数据
            loadPageData(page);
        });
    });

    // 联系人标签切换
    document.querySelectorAll('.contact-tabs .tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const listType = this.dataset.tab;
            
            // 更新标签激活状态
            document.querySelectorAll('.contact-tabs .tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // 显示对应列表
            document.querySelectorAll('.contact-list').forEach(list => {
                list.style.display = 'none';
                list.classList.remove('active');
            });
            const targetList = document.getElementById(`${listType}-list`);
            targetList.style.display = 'block';
            targetList.classList.add('active');
        });
    });

    // 联系人搜索
    document.getElementById('contact-search').addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const activeList = document.querySelector('.contact-list.active');
        const rows = activeList.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = Array.from(row.cells)
                .map(cell => cell.textContent.toLowerCase())
                .join(' ');
            row.style.display = text.includes(searchText) ? '' : 'none';
        });
    });

    // 配置保存
    document.getElementById('save-config').addEventListener('click', async function() {
        try {
            const config = {};
            document.querySelectorAll('.config-item input, .config-item select').forEach(input => {
                const path = input.name.split('.');
                let current = config;
                
                // 处理数组类型的配置项
                if (input.name.endsWith('[]')) {
                    const arrayPath = input.name.slice(0, -2).split('.');
                    let arrayParent = config;
                    for (let i = 0; i < arrayPath.length - 1; i++) {
                        if (!arrayParent[arrayPath[i]]) {
                            arrayParent[arrayPath[i]] = {};
                        }
                        arrayParent = arrayParent[arrayPath[i]];
                    }
                    const lastKey = arrayPath[arrayPath.length - 1];
                    if (!arrayParent[lastKey]) {
                        arrayParent[lastKey] = [];
                    }
                    if (input.value) {
                        arrayParent[lastKey].push(input.value);
                    }
                    return;
                }
                
                // 处理普通配置项
                for (let i = 0; i < path.length - 1; i++) {
                    if (!current[path[i]]) {
                        current[path[i]] = {};
                    }
                    current = current[path[i]];
                }
                
                // 根据输入类型设置值
                const value = input.type === 'checkbox' ? input.checked :
                             input.type === 'number' ? Number(input.value) :
                             input.value;
                current[path[path.length - 1]] = value;
            });

            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                showNotification('配置保存成功！', 'success');
            } else {
                showNotification('配置保存失败！', 'error');
            }
        } catch (error) {
            console.error('保存配置出错：', error);
            showNotification('保存配置时发生错误！', 'error');
        }
    });

    // 重置配置
    document.getElementById('reset-config').addEventListener('click', function() {
        loadConfig();
    });

    // 添加管理员
    document.getElementById('add-admin').addEventListener('click', function() {
        const adminList = document.getElementById('admin-list');
        const adminItem = document.createElement('div');
        adminItem.className = 'admin-item d-flex align-items-center gap-2 mb-2';
        adminItem.innerHTML = `
            <input type="text" class="form-control" name="XYBot.admins[]" placeholder="输入管理员wxid">
            <button class="btn btn-danger btn-sm remove-admin">
                <i class="fas fa-times"></i>
            </button>
        `;
        adminList.appendChild(adminItem);

        // 绑定删除按钮事件
        adminItem.querySelector('.remove-admin').addEventListener('click', function() {
            adminItem.remove();
        });
    });

    // 初始加载
    loadPageData('contacts');
    updateStatus();
    initMessageChart();
    setInterval(updateStatus, 30000); // 每30秒更新一次状态
});

async function loadPageData(page) {
    switch(page) {
        case 'contacts':
            await loadContacts();
            break;
        case 'config':
            await loadConfig();
            break;
        case 'plugins':
            await loadPlugins();
            break;
        case 'status':
            await loadStatus();
            break;
    }
}

async function loadContacts() {
    try {
        const response = await fetch('/api/contacts');
        const contacts = await response.json();
        
        const friendsTable = document.getElementById('friends-table');
        const groupsTable = document.getElementById('groups-table');
        friendsTable.innerHTML = '';
        groupsTable.innerHTML = '';
        
        contacts.forEach(contact => {
            const tr = document.createElement('tr');
            const avatarHtml = contact.avatar ? 
                `<img src="${contact.avatar}" alt="头像">` : 
                contact.type === '群聊' ? '👥' : '👤';
                
            if (contact.type === '群聊') {
                tr.innerHTML = `
                    <td><div class="avatar">${avatarHtml}</div></td>
                    <td>${contact.wxid}</td>
                    <td>${contact.nickname || '未知群聊'}</td>
                    <td>${contact.member_count || 0}</td>
                    <td>
                        <div class="form-check form-switch">
                            <input class="form-check-input ai-toggle" type="checkbox" 
                                data-wxid="${contact.wxid}" 
                                ${contact.ai_enabled ? 'checked' : ''}>
                        </div>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary btn-action">
                            <i class="fas fa-info-circle"></i> 详情
                        </button>
                        <button class="btn btn-sm btn-info btn-action">
                            <i class="fas fa-users"></i> 成员
                        </button>
                    </td>
                `;
                groupsTable.appendChild(tr);
            } else {
                tr.innerHTML = `
                    <td><div class="avatar">${avatarHtml}</div></td>
                    <td>${contact.wxid}</td>
                    <td>${contact.nickname || '未知用户'}</td>
                    <td>${contact.remark || '-'}</td>
                    <td>
                        <div class="form-check form-switch">
                            <input class="form-check-input ai-toggle" type="checkbox" 
                                data-wxid="${contact.wxid}" 
                                ${contact.ai_enabled ? 'checked' : ''}>
                        </div>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary btn-action">
                            <i class="fas fa-info-circle"></i> 详情
                        </button>
                    </td>
                `;
                friendsTable.appendChild(tr);
            }
        });

        // 绑定AI开关事件
        document.querySelectorAll('.ai-toggle').forEach(toggle => {
            toggle.addEventListener('change', async function() {
                const wxid = this.dataset.wxid;
                const enabled = this.checked;
                try {
                    const response = await fetch('/api/toggle_ai', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            wxid: wxid,
                            enabled: enabled
                        })
                    });
                    
                    if (response.ok) {
                        showNotification(`已${enabled ? '开启' : '关闭'} ${wxid} 的AI功能`, 'success');
                    } else {
                        showNotification('操作失败', 'error');
                        this.checked = !enabled; // 恢复原状态
                    }
                } catch (error) {
                    console.error('切换AI状态失败：', error);
                    showNotification('操作失败', 'error');
                    this.checked = !enabled; // 恢复原状态
                }
            });
        });

    } catch (error) {
        console.error('加载联系人失败：', error);
        showNotification('加载联系人失败！', 'error');
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        // 填充配置表单
        document.querySelectorAll('.config-item input, .config-item select').forEach(input => {
            const path = input.name.split('.');
            let value = config;
            for (const key of path) {
                if (value) {
                    value = value[key];
                }
            }
            if (value !== undefined) {
                input.value = value;
            }
        });

        // 填充管理员列表
        const adminList = document.getElementById('admin-list');
        adminList.innerHTML = '';
        if (config.XYBot && Array.isArray(config.XYBot.admins)) {
            config.XYBot.admins.forEach(admin => {
                const adminItem = document.createElement('div');
                adminItem.className = 'admin-item d-flex align-items-center gap-2 mb-2';
                adminItem.innerHTML = `
                    <input type="text" class="form-control" name="XYBot.admins[]" value="${admin}">
                    <button class="btn btn-danger btn-sm remove-admin">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                adminList.appendChild(adminItem);

                // 绑定删除按钮事件
                adminItem.querySelector('.remove-admin').addEventListener('click', function() {
                    adminItem.remove();
                });
            });
        }

        // 加载插件配置
        const pluginsConfig = document.getElementById('plugins-config');
        pluginsConfig.innerHTML = '<h3>插件配置</h3>';
        
        if (config.Plugins) {
            Object.entries(config.Plugins).forEach(([pluginName, settings]) => {
                const section = document.createElement('div');
                section.className = 'plugin-config-section mb-4';
                section.innerHTML = `<h4 class="mb-3">${pluginName}</h4>`;
                
                Object.entries(settings).forEach(([key, value]) => {
                    const item = document.createElement('div');
                    item.className = 'config-item';
                    
                    if (typeof value === 'boolean') {
                        item.innerHTML = `
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="Plugins.${pluginName}.${key}" 
                                    ${value ? 'checked' : ''}>
                                <label class="form-check-label">${key}</label>
                            </div>
                        `;
                    } else if (Array.isArray(value)) {
                        item.innerHTML = `
                            <label>${key}</label>
                            <div class="array-input-container">
                                ${value.map(v => `
                                    <div class="d-flex gap-2 mb-2">
                                        <input type="text" class="form-control" 
                                            name="Plugins.${pluginName}.${key}[]" value="${v}">
                                        <button class="btn btn-danger btn-sm remove-item">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </div>
                                `).join('')}
                                <button class="btn btn-sm btn-primary add-array-item" 
                                    data-plugin="${pluginName}" data-key="${key}">
                                    <i class="fas fa-plus"></i> 添加项
                                </button>
                            </div>
                        `;
                    } else {
                        item.innerHTML = `
                            <label>${key}</label>
                            <input type="${typeof value === 'number' ? 'number' : 'text'}" 
                                class="form-control" name="Plugins.${pluginName}.${key}" 
                                value="${value}">
                        `;
                    }
                    
                    section.appendChild(item);
                });
                
                pluginsConfig.appendChild(section);
            });
            
            // 绑定数组项添加按钮事件
            document.querySelectorAll('.add-array-item').forEach(button => {
                button.addEventListener('click', function() {
                    const container = this.closest('.array-input-container');
                    const newItem = document.createElement('div');
                    newItem.className = 'd-flex gap-2 mb-2';
                    newItem.innerHTML = `
                        <input type="text" class="form-control" 
                            name="Plugins.${this.dataset.plugin}.${this.dataset.key}[]" value="">
                        <button class="btn btn-danger btn-sm remove-item">
                            <i class="fas fa-times"></i>
                        </button>
                    `;
                    container.insertBefore(newItem, this);
                    
                    // 绑定删除按钮事件
                    newItem.querySelector('.remove-item').addEventListener('click', function() {
                        this.closest('.d-flex').remove();
                    });
                });
            });
            
            // 绑定数组项删除按钮事件
            document.querySelectorAll('.remove-item').forEach(button => {
                button.addEventListener('click', function() {
                    this.closest('.d-flex').remove();
                });
            });
        }
    } catch (error) {
        console.error('加载配置失败：', error);
        showNotification('加载配置失败！', 'error');
    }
}

async function loadPlugins() {
    try {
        const response = await fetch('/api/plugins');
        const plugins = await response.json();
        
        const grid = document.getElementById('plugins-list');
        grid.innerHTML = '';
        
        plugins.forEach(plugin => {
            const card = document.createElement('div');
            card.className = 'plugin-card';
            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">${plugin.name}</h5>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" ${plugin.enabled ? 'checked' : ''}>
                    </div>
                </div>
                <div class="plugin-description text-muted">
                    ${plugin.description || '暂无描述'}
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (error) {
        console.error('加载插件列表失败：', error);
        showNotification('加载插件列表失败！', 'error');
    }
}

async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        document.getElementById('login-status').textContent = status.logged_in ? '已登录' : '未登录';
        document.getElementById('system-uptime').textContent = status.uptime || '未知';
        document.getElementById('cpu-usage').textContent = status.cpu_usage || '未知';
        document.getElementById('memory-usage').textContent = status.memory_usage || '未知';
        
        updateMessageChart(status.message_stats);
    } catch (error) {
        console.error('加载状态失败：', error);
        showNotification('加载状态失败！', 'error');
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        const statusBar = document.getElementById('status-bar');
        const botStatus = document.getElementById('bot-status');
        
        if (status.logged_in) {
            botStatus.innerHTML = '<i class="fas fa-check-circle text-success"></i> 机器人正常运行中';
        } else {
            botStatus.innerHTML = '<i class="fas fa-exclamation-circle text-danger"></i> 机器人未登录';
        }
        
        document.getElementById('uptime').textContent = `运行时间: ${status.uptime || '未知'}`;
        document.getElementById('message-count').textContent = `消息数: ${status.message_count || '0'}`;
    } catch (error) {
        console.error('更新状态失败：', error);
        const botStatus = document.getElementById('bot-status');
        botStatus.innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i> 无法获取状态';
    }
}

function showNotification(message, type = 'info') {
    // 确保存在通知容器
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // 添加到容器
    container.appendChild(notification);
    
    // 动画显示
    setTimeout(() => notification.classList.add('show'), 100);
    
    // 3秒后移除
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

let messageChart = null;

function initMessageChart() {
    const ctx = document.getElementById('message-chart').getContext('2d');
    messageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '消息数量',
                data: [],
                borderColor: '#00a8ff',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(0, 168, 255, 0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#718093'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#718093'
                    }
                }
            }
        }
    });
}

function updateMessageChart(stats) {
    if (!messageChart || !stats) return;
    
    messageChart.data.labels = stats.labels || [];
    messageChart.data.datasets[0].data = stats.data || [];
    messageChart.update();
} 