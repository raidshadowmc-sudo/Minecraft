
// Enhanced Target List Management System
// Supports advanced filtering, reactions, tags, and priority management with stunning visual effects

class TargetListManager {
    constructor() {
        this.targets = [];
        this.filteredTargets = [];
        this.isLoading = false;
        this.particleInterval = null;
        this.init();
    }

    init() {
        console.log('🎯 Initializing Enhanced Target List System...');
        this.setupEventListeners();
        this.loadTargets();
        this.setupCharacterCounters();
        this.createAdvancedParticleSystem();
        this.setupAdvancedEffects();
        console.log('✅ Target List System initialized successfully!');
    }

    createAdvancedParticleSystem() {
        const particleSystem = document.getElementById('particleSystem');
        if (!particleSystem) return;

        // Create continuous floating particles
        this.particleInterval = setInterval(() => {
            this.createFloatingParticle(particleSystem);
        }, 1500);

        // Create background pattern particles
        this.createBackgroundParticles(particleSystem);
    }

    createFloatingParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'floating-particle';
        
        // Random starting position
        particle.style.left = Math.random() * 100 + '%';
        particle.style.bottom = '-10px';
        
        // Random size and color variation
        const size = 3 + Math.random() * 4;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        
        // Color variations
        const colors = ['#dc3545', '#ff1744', '#d50000', '#ff6b6b'];
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];
        
        const animation = particle.animate([
            { 
                transform: 'translateY(0px) rotate(0deg)', 
                opacity: 0,
                filter: 'blur(0px)'
            },
            { 
                transform: 'translateY(-100px) rotate(180deg)', 
                opacity: 1,
                filter: 'blur(1px)',
                offset: 0.1 
            },
            { 
                transform: `translateY(-${window.innerHeight + 100}px) rotate(360deg)`, 
                opacity: 0,
                filter: 'blur(2px)'
            }
        ], {
            duration: 8000 + Math.random() * 4000,
            easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
        });

        container.appendChild(particle);

        animation.onfinish = () => {
            if (particle.parentNode) {
                particle.remove();
            }
        };
    }

    createBackgroundParticles(container) {
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                particle.style.cssText = `
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    background: rgba(220, 53, 69, 0.3);
                    border-radius: 50%;
                    left: ${Math.random() * 100}%;
                    top: ${Math.random() * 100}%;
                    box-shadow: 0 0 4px rgba(220, 53, 69, 0.5);
                    animation: twinkle 3s ease-in-out infinite;
                `;
                
                container.appendChild(particle);
            }, i * 200);
        }
    }

    setupAdvancedEffects() {
        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes twinkle {
                0%, 100% { opacity: 0.3; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.5); }
            }
            
            @keyframes cardGlow {
                0% { box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }
                100% { box-shadow: 0 20px 40px rgba(220, 53, 69, 0.4), 0 0 30px rgba(220, 53, 69, 0.3); }
            }
            
            .target-removing {
                animation: removeTarget 0.5s ease-out forwards;
            }
            
            @keyframes removeTarget {
                0% { 
                    transform: scale(1) rotateX(0deg);
                    opacity: 1;
                }
                50% {
                    transform: scale(0.9) rotateX(45deg);
                    opacity: 0.5;
                }
                100% { 
                    transform: scale(0) rotateX(90deg);
                    opacity: 0;
                    height: 0;
                    margin: 0;
                    padding: 0;
                }
            }
            
            .skull-glitch-effect {
                animation: skullGlitchIntense 0.3s ease-in-out;
            }
            
            @keyframes skullGlitchIntense {
                0%, 100% { transform: translate(0); filter: hue-rotate(0deg); }
                10% { transform: translate(-3px, 2px); filter: hue-rotate(90deg); }
                20% { transform: translate(3px, -2px); filter: hue-rotate(180deg); }
                30% { transform: translate(-2px, -3px); filter: hue-rotate(270deg); }
                40% { transform: translate(2px, 3px); filter: hue-rotate(360deg); }
                50% { transform: translate(-1px, 1px); filter: hue-rotate(45deg); }
                60% { transform: translate(1px, -1px); filter: hue-rotate(135deg); }
                70% { transform: translate(-2px, 2px); filter: hue-rotate(225deg); }
                80% { transform: translate(2px, -2px); filter: hue-rotate(315deg); }
                90% { transform: translate(-1px, -1px); filter: hue-rotate(180deg); }
            }
        `;
        document.head.appendChild(style);

        // Setup skull advanced effects
        this.setupSkullAdvancedEffects();
    }

    setupSkullAdvancedEffects() {
        const mainSkull = document.getElementById('mainSkull');
        const skullIcon = document.querySelector('.skull-icon');
        
        if (!mainSkull || !skullIcon) return;

        let isGlitching = false;

        mainSkull.addEventListener('mouseenter', () => {
            this.createEnhancedSkullParticles();
            skullIcon.style.filter = 'drop-shadow(0 0 20px #ff1744) drop-shadow(0 0 40px #dc3545)';
            skullIcon.style.zIndex = '10';
        });

        mainSkull.addEventListener('mouseleave', () => {
            skullIcon.style.filter = '';
            skullIcon.style.zIndex = '';
        });

        mainSkull.addEventListener('click', () => {
            if (isGlitching) return;
            
            isGlitching = true;
            skullIcon.classList.add('skull-glitch-effect');
            this.createExplosionEffect();
            
            setTimeout(() => {
                skullIcon.classList.remove('skull-glitch-effect');
                isGlitching = false;
            }, 300);
        });
    }

    createEnhancedSkullParticles() {
        const container = document.getElementById('skullParticles');
        if (!container) return;

        const particles = 15;

        for (let i = 0; i < particles; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                const size = 4 + Math.random() * 4;
                const colors = ['#dc3545', '#ff1744', '#d50000', '#c62828'];
                
                particle.style.cssText = `
                    position: absolute;
                    width: ${size}px;
                    height: ${size}px;
                    background: ${colors[Math.floor(Math.random() * colors.length)]};
                    border-radius: 50%;
                    pointer-events: none;
                    left: 50%;
                    top: 50%;
                    opacity: 0;
                    z-index: 0;
                    box-shadow: 0 0 ${size * 2}px currentColor;
                `;

                const animation = particle.animate([
                    { 
                        opacity: 0, 
                        transform: 'translate(-50%, -50%) translateY(0px) rotate(0deg) scale(0.3)',
                        filter: 'blur(0px)'
                    },
                    { 
                        opacity: 1, 
                        transform: 'translate(-50%, -50%) translateY(-40px) rotate(180deg) scale(1)',
                        filter: 'blur(1px)',
                        offset: 0.3
                    },
                    { 
                        opacity: 0, 
                        transform: 'translate(-50%, -50%) translateY(-80px) rotate(360deg) scale(0.1)',
                        filter: 'blur(3px)'
                    }
                ], {
                    duration: 2500,
                    easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
                });

                animation.onfinish = () => {
                    if (particle.parentNode) {
                        particle.remove();
                    }
                };

                container.appendChild(particle);
            }, i * 80);
        }
    }

    createExplosionEffect() {
        const skull = document.getElementById('mainSkull');
        if (!skull) return;

        // Create explosion particles
        for (let i = 0; i < 25; i++) {
            const particle = document.createElement('div');
            const size = 2 + Math.random() * 3;
            
            particle.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: #ff1744;
                border-radius: 50%;
                pointer-events: none;
                left: 50%;
                top: 50%;
                opacity: 1;
                z-index: 0;
                box-shadow: 0 0 10px #ff1744;
            `;

            const angle = (360 / 25) * i;
            const distance = 50 + Math.random() * 50;
            const duration = 800 + Math.random() * 400;

            const animation = particle.animate([
                { 
                    transform: 'translate(-50%, -50%) translate(0px, 0px) scale(1)',
                    opacity: 1 
                },
                { 
                    transform: `translate(-50%, -50%) translate(${Math.cos(angle * Math.PI / 180) * distance}px, ${Math.sin(angle * Math.PI / 180) * distance}px) scale(0)`,
                    opacity: 0 
                }
            ], {
                duration: duration,
                easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            });

            animation.onfinish = () => {
                if (particle.parentNode) {
                    particle.remove();
                }
            };

            skull.appendChild(particle);
        }
    }

    setupEventListeners() {
        // Add target button
        const addBtn = document.getElementById('addTargetBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.openAddTargetModal();
            });
        }

        // Form submissions
        const addForm = document.getElementById('addTargetForm');
        if (addForm) {
            addForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAddTarget();
            });
        }

        // Filters
        this.setupFilterListeners();
    }

    setupFilterListeners() {
        const filters = [
            { id: 'gamemodeFilter', handler: () => this.applyFilters() },
            { id: 'priorityFilter', handler: () => this.applyFilters() },
            { id: 'searchFilter', handler: this.debounce(() => this.applyFilters(), 300) },
            { id: 'tagsFilter', handler: this.debounce(() => this.applyFilters(), 300) }
        ];

        filters.forEach(filter => {
            const element = document.getElementById(filter.id);
            if (element && typeof element.addEventListener === 'function') {
                const eventType = element.tagName === 'INPUT' ? 'input' : 'change';
                element.addEventListener(eventType, filter.handler);
                console.log(`✅ Filter listener added for ${filter.id}`);
            } else if (element) {
                console.warn(`⚠️ Element ${filter.id} found but addEventListener not available`);
            } else {
                console.warn(`⚠️ Filter element ${filter.id} not found`);
            }
        });
    }

    setupCharacterCounters() {
        // Reason counter
        const reasonField = document.querySelector('[name="reason"]');
        const reasonCounter = document.getElementById('reasonLength');
        if (reasonField && reasonCounter) {
            reasonField.addEventListener('input', (e) => {
                const length = e.target.value.length;
                reasonCounter.textContent = length;
                
                // Color coding
                if (length > 300) {
                    reasonCounter.style.color = '#dc3545';
                } else if (length > 250) {
                    reasonCounter.style.color = '#ffc107';
                } else {
                    reasonCounter.style.color = '#6c757d';
                }
            });
        }

        // Description counter
        const descField = document.querySelector('[name="description"]');
        if (descField) {
            descField.addEventListener('input', (e) => {
                const maxLength = 500;
                const length = e.target.value.length;
                
                if (length > maxLength) {
                    e.target.value = e.target.value.substring(0, maxLength);
                }
            });
        }
    }

    async loadTargets() {
        this.showLoading(true);
        try {
            const response = await fetch('/api/targets?status=active');
            const data = await response.json();
            
            if (data.success) {
                this.targets = data.targets || [];
                this.applyFilters();
                this.updateStatistics();
            } else {
                console.warn('API returned error:', data.error);
                this.loadMockData(); // Fallback to mock data
            }
        } catch (error) {
            console.error('Error loading targets:', error);
            this.loadMockData(); // Fallback to mock data
        } finally {
            this.showLoading(false);
        }
    }

    loadMockData() {
        console.log('Loading mock data for demonstration...');
        this.targets = [
            {
                id: 1,
                nickname: "TestPlayer1",
                server: "hypixel.net",
                gamemode: "bedwars",
                reason: "Использование читов в игре. Подозрительные движения и реакции.",
                priority: "high",
                status: "active",
                date_added: new Date().toISOString(),
                added_by: "Admin",
                tags: ["чит", "подозрительный"],
                description: "Замечен в использовании aimbot и wallhack",
                total_reactions: 15,
                has_bleeding_effect: true,
                fragged_count: 3,
                killed_count: 5,
                exploded_count: 2,
                likes: 8,
                dislikes: 1
            },
            {
                id: 2,
                nickname: "ToxicPlayer99",
                server: "minemen.club",
                gamemode: "kitpvp",
                reason: "Токсичное поведение в чате, оскорбления других игроков",
                priority: "medium",
                status: "active",
                date_added: new Date(Date.now() - 86400000).toISOString(),
                added_by: "Moderator",
                tags: ["токсик", "чат"],
                description: "Неоднократные жалобы на поведение",
                total_reactions: 7,
                has_bleeding_effect: false,
                fragged_count: 1,
                killed_count: 2,
                exploded_count: 1,
                likes: 5,
                dislikes: 2
            },
            {
                id: 3,
                nickname: "SpeedHacker",
                server: "cubecraft.net",
                gamemode: "skywars",
                reason: "Скоростные читы, телепортация",
                priority: "critical",
                status: "active",
                date_added: new Date(Date.now() - 172800000).toISOString(),
                added_by: "Admin",
                tags: ["чит", "скорость", "телепорт"],
                description: "Критические нарушения правил сервера",
                total_reactions: 25,
                has_bleeding_effect: true,
                fragged_count: 8,
                killed_count: 7,
                exploded_count: 4,
                likes: 15,
                dislikes: 0
            }
        ];
        this.applyFilters();
        this.updateStatistics();
    }

    applyFilters() {
        const gamemodeFilter = document.getElementById('gamemodeFilter')?.value || '';
        const priorityFilter = document.getElementById('priorityFilter')?.value || '';
        const searchFilter = document.getElementById('searchFilter')?.value.toLowerCase().trim() || '';
        const tagsFilter = document.getElementById('tagsFilter')?.value.toLowerCase().trim() || '';

        this.filteredTargets = this.targets.filter(target => {
            // Gamemode filter
            if (gamemodeFilter && target.gamemode !== gamemodeFilter) return false;
            
            // Priority filter
            if (priorityFilter && target.priority !== priorityFilter) return false;
            
            // Search filter
            if (searchFilter) {
                const searchableText = `${target.nickname} ${target.server} ${target.reason}`.toLowerCase();
                if (!searchableText.includes(searchFilter)) return false;
            }
            
            // Tags filter
            if (tagsFilter && target.tags) {
                const filterTags = tagsFilter.split(',').map(tag => tag.trim()).filter(tag => tag);
                const targetTags = target.tags.map(tag => tag.toLowerCase());
                const hasMatchingTag = filterTags.some(filterTag => 
                    targetTags.some(targetTag => targetTag.includes(filterTag))
                );
                if (!hasMatchingTag) return false;
            }
            
            return true;
        });

        this.renderTargets();
    }

    renderTargets() {
        const container = document.getElementById('targetItems');
        const emptyState = document.getElementById('emptyState');

        if (!container) return;

        if (this.filteredTargets.length === 0) {
            container.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        // Sort by priority rank and date
        const sortedTargets = [...this.filteredTargets].sort((a, b) => {
            const priorityRanks = { critical: 4, high: 3, medium: 2, low: 1 };
            const rankA = priorityRanks[a.priority] || 2;
            const rankB = priorityRanks[b.priority] || 2;
            
            if (rankA !== rankB) {
                return rankB - rankA; // Higher priority first
            }
            return new Date(b.date_added) - new Date(a.date_added);
        });

        container.innerHTML = sortedTargets.map((target, index) => 
            this.createTargetCard(target, index)
        ).join('');
    }

    createTargetCard(target, index) {
        const totalReactions = target.total_reactions || 0;
        const isBloodied = totalReactions >= 10 || target.has_bleeding_effect;
        const priorityClass = `priority-${target.priority}`;
        
        const reactions = [
            { type: 'fragged', count: target.fragged_count || 0, icon: '🗡️', label: 'Убит' },
            { type: 'killed', count: target.killed_count || 0, icon: '⚔️', label: 'Сражен' },
            { type: 'exploded', count: target.exploded_count || 0, icon: '💥', label: 'Взорван' },
            { type: 'slayed', count: target.slayed_count || 0, icon: '🔪', label: 'Зарезан' }
        ];

        const tagsHtml = target.tags && target.tags.length > 0 
            ? `<div class="target-tags mt-2">
                ${target.tags.map(tag => `<span class="badge bg-danger me-1" style="font-size: 0.7rem;">${this.escapeHtml(tag)}</span>`).join('')}
               </div>`
            : '';

        const descriptionHtml = target.description 
            ? `<div class="target-description mb-2" style="background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #17a2b8;">
                <strong style="color: #17a2b8;"><i class="fas fa-info-circle me-1"></i>Заметки:</strong><br>
                <span style="color: rgba(255,255,255,0.9);">${this.escapeHtml(target.description)}</span>
               </div>`
            : '';

        const canEdit = typeof isAdmin !== 'undefined' && isAdmin || 
                       (typeof currentPlayer !== 'undefined' && currentPlayer && target.added_by === currentPlayer.nickname);

        return `
            <div class="enhanced-target-card ${isBloodied ? 'bloodied' : ''}" 
                 data-priority="${target.priority}" 
                 data-target-id="${target.id}"
                 style="animation-delay: ${index * 0.1}s">
                <div class="target-glow-effect"></div>
                
                <div class="target-item-header">
                    <div class="target-main-info">
                        <div class="target-nickname-container">
                            <i class="fas fa-crosshairs target-icon"></i>
                            <span class="target-nickname">${this.escapeHtml(target.nickname)}</span>
                        </div>
                        <div class="target-badges">
                            <span class="gamemode-badge ${target.gamemode}">
                                <i class="fas fa-gamepad me-1"></i>${target.gamemode.toUpperCase()}
                            </span>
                            <span class="priority-badge ${priorityClass}">
                                ${this.getPriorityIcon(target.priority)} ${this.getPriorityText(target.priority)}
                            </span>
                            ${totalReactions > 0 ? `<span class="badge bg-warning text-dark"><i class="fas fa-fire me-1"></i>${totalReactions} реакций</span>` : ''}
                        </div>
                        ${tagsHtml}
                    </div>
                </div>

                <div class="server-info-card">
                    <i class="fas fa-server server-icon"></i>
                    <div class="server-details">
                        <span class="server-label">Сервер:</span>
                        <span class="server-name">${this.escapeHtml(target.server)}</span>
                    </div>
                </div>

                <div class="target-reason-container">
                    <div class="reason-header">
                        <i class="fas fa-scroll me-2"></i>
                        <span>Причина добавления:</span>
                    </div>
                    <div class="target-reason">${this.escapeHtml(target.reason)}</div>
                </div>

                ${descriptionHtml}

                ${reactions.some(r => r.count > 0) ? `
                <div class="target-reactions mb-3">
                    <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                        <h6 style="color: #dc3545; margin-bottom: 0.75rem;"><i class="fas fa-fire me-2"></i>Реакции сообщества:</h6>
                        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                            ${reactions.filter(r => r.count > 0).map(reaction => `
                                <span style="background: rgba(220,53,69,0.2); padding: 0.4rem 0.8rem; border-radius: 15px; border: 1px solid rgba(220,53,69,0.3); font-size: 0.8rem;">
                                    ${reaction.icon} ${reaction.count}
                                </span>
                            `).join('')}
                        </div>
                        <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem;">
                            <span style="background: rgba(40,167,69,0.2); padding: 0.3rem 0.6rem; border-radius: 12px; font-size: 0.75rem;">
                                👍 ${target.likes || 0}
                            </span>
                            <span style="background: rgba(220,53,69,0.2); padding: 0.3rem 0.6rem; border-radius: 12px; font-size: 0.75rem;">
                                👎 ${target.dislikes || 0}
                            </span>
                        </div>
                    </div>
                </div>
                ` : ''}

                <div class="target-actions">
                    ${canEdit ? `
                        <button class="btn-action btn-edit" onclick="targetManager.editTarget(${target.id})">
                            <i class="fas fa-edit"></i>
                            <span>Изменить</span>
                        </button>
                    ` : ''}
                    ${typeof isAdmin !== 'undefined' && isAdmin ? `
                        <button class="btn-action btn-complete" onclick="targetManager.completeTarget(${target.id})">
                            <i class="fas fa-check"></i>
                            <span>Устранен</span>
                        </button>
                        <button class="btn-action btn-delete" onclick="targetManager.deleteTarget(${target.id})">
                            <i class="fas fa-trash"></i>
                            <span>Удалить</span>
                        </button>
                    ` : ''}
                </div>

                <div class="target-footer mt-3 pt-3" style="border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.8rem; color: rgba(255,255,255,0.6);">
                    <i class="fas fa-calendar me-1"></i>
                    Добавлено: ${this.formatDate(target.date_added)} | 
                    Автор: ${this.escapeHtml(target.added_by || 'Неизвестно')}
                    ${target.last_updated && target.last_updated !== target.date_added ? 
                        ` | Обновлено: ${this.formatDate(target.last_updated)}` : ''}
                </div>
            </div>
        `;
    }

    getPriorityIcon(priority) {
        const icons = {
            'low': '<i class="fas fa-info-circle me-1"></i>',
            'medium': '<i class="fas fa-exclamation-circle me-1"></i>',
            'high': '<i class="fas fa-exclamation-triangle me-1"></i>',
            'critical': '<i class="fas fa-skull me-1"></i>'
        };
        return icons[priority] || icons['medium'];
    }

    getPriorityText(priority) {
        const texts = {
            'low': 'НИЗКИЙ',
            'medium': 'СРЕДНИЙ',
            'high': 'ВЫСОКИЙ',
            'critical': 'КРИТИЧЕСКИЙ'
        };
        return texts[priority] || 'СРЕДНИЙ';
    }

    async handleAddTarget() {
        const formData = new FormData(document.getElementById('addTargetForm'));
        
        const nickname = formData.get('nickname').trim();
        const gamemode = formData.get('gamemode');
        const server = formData.get('server').trim();
        const priority = formData.get('priority');
        const tagsInput = formData.get('tags').trim();
        const reason = formData.get('reason').trim();
        const description = formData.get('description').trim();

        // Validation
        if (!nickname || !gamemode || !server || !reason) {
            this.showError('Заполните все обязательные поля!');
            return;
        }

        if (nickname.length > 20) {
            this.showError('Никнейм не должен превышать 20 символов!');
            return;
        }

        if (reason.length > 320) {
            this.showError('Причина не должна превышать 320 символов!');
            return;
        }

        // Parse tags
        const tags = tagsInput ? tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

        const data = {
            nickname,
            gamemode,
            server,
            priority,
            priority_rank: this.getPriorityRank(priority),
            tags,
            reason,
            description
        };

        try {
            const response = await fetch('/api/targets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(result.message || 'Цель успешно добавлена!');
                this.loadTargets(); // Reload targets
                this.closeModal('addTargetModal');
                this.resetForm('addTargetForm');
                this.createExplosionEffect(); // Visual feedback
            } else {
                this.showError('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Error adding target:', error);
            this.showError('Не удалось добавить цель');
        }
    }

    async deleteTarget(targetId) {
        if (!confirm('Вы уверены, что хотите удалить эту цель?')) return;

        try {
            // Add removal animation
            const targetElement = document.querySelector(`[data-target-id="${targetId}"]`);
            if (targetElement) {
                targetElement.classList.add('target-removing');
            }

            const response = await fetch(`/api/targets/${targetId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(result.message || 'Цель успешно удалена!');
                
                setTimeout(() => {
                    this.loadTargets();
                }, 500);
            } else {
                // Remove animation if failed
                if (targetElement) {
                    targetElement.classList.remove('target-removing');
                }
                this.showError('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Error deleting target:', error);
            this.showError('Не удалось удалить цель');
        }
    }

    async completeTarget(targetId) {
        if (!confirm('Отметить эту цель как выполненную?')) return;

        try {
            const response = await fetch(`/api/targets/${targetId}/complete`, {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(result.message || 'Цель отмечена как выполненная!');
                this.loadTargets();
                this.createExplosionEffect(); // Visual feedback
            } else {
                this.showError('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Error completing target:', error);
            this.showError('Не удалось отметить цель как выполненную');
        }
    }

    updateStatistics() {
        const today = new Date().toDateString();
        
        const stats = {
            total: this.targets.length,
            active: this.targets.filter(t => t.status === 'active').length,
            completed: this.targets.filter(t => t.status === 'completed').length,
            today: this.targets.filter(t => new Date(t.date_added).toDateString() === today).length
        };

        // Animate number changes
        this.animateNumber('totalTargets', stats.total);
        this.animateNumber('activeTargets', stats.active);
        this.animateNumber('completedTargets', stats.completed);
        this.animateNumber('todayTargets', stats.today);
    }

    animateNumber(elementId, targetValue) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const currentValue = parseInt(element.textContent) || 0;
        const increment = Math.ceil((targetValue - currentValue) / 10);
        
        if (currentValue !== targetValue) {
            const timer = setInterval(() => {
                const current = parseInt(element.textContent) || 0;
                if (current < targetValue) {
                    element.textContent = Math.min(current + increment, targetValue);
                } else {
                    element.textContent = targetValue;
                    clearInterval(timer);
                }
            }, 50);
        }
    }

    // Utility methods
    getPriorityRank(priority) {
        const ranks = { low: 1, medium: 2, high: 3, critical: 4 };
        return ranks[priority] || 2;
    }

    openAddTargetModal() {
        const modal = new bootstrap.Modal(document.getElementById('addTargetModal'));
        modal.show();
    }

    closeModal(modalId) {
        const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        if (modal) modal.hide();
    }

    resetForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
            // Reset character counters
            const reasonCounter = document.getElementById('reasonLength');
            if (reasonCounter) reasonCounter.textContent = '0';
        }
    }

    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) {
            spinner.style.display = show ? 'block' : 'none';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // Create notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'}" style="font-size: 1.2rem;"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; font-size: 1.1rem; cursor: pointer; margin-left: auto;">×</button>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? 'linear-gradient(45deg, #28a745, #20c997)' : 
                         type === 'error' ? 'linear-gradient(45deg, #dc3545, #c82333)' : 
                         'linear-gradient(45deg, #17a2b8, #20c997)'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            z-index: 9999;
            transform: translateX(400px);
            transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            max-width: 400px;
            border: 1px solid rgba(255,255,255,0.2);
        `;
        
        document.body.appendChild(notification);
        
        // Show animation
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto-hide
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.transform = 'translateX(400px)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 400);
            }
        }, 5000);
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatDate(dateString) {
        if (!dateString) return 'Неизвестно';
        return new Date(dateString).toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Cleanup method
    destroy() {
        if (this.particleInterval) {
            clearInterval(this.particleInterval);
        }
    }

    // Public methods for global access
    editTarget(targetId) {
        console.log('Edit target:', targetId);
        // TODO: Implement edit functionality with modal
        this.showNotification('Функция редактирования будет добавлена в ближайшее время', 'info');
    }
}

// Global variables for template access
window.targetManager = null;

// Global functions for template access
window.addTarget = function() {
    if (window.targetManager) {
        window.targetManager.handleAddTarget();
    }
};

// Initialize the target list manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 DOM loaded, initializing Target List Manager...');
    
    // Only initialize if we're on the target list page
    if (document.getElementById('targetItems')) {
        window.targetManager = new TargetListManager();
        console.log('✅ Target List Manager initialized and available globally');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.targetManager) {
        window.targetManager.destroy();
    }
});
