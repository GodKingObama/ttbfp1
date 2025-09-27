class TikTokClone {
    constructor() {
        this.currentUser = null;
        this.currentFeed = 'foryou';
        this.currentPage = 1;
        this.isLoading = false;
        this.mediaItems = [];
        this.currentMediaIndex = 0;
        
        this.init();
    }
    
    init() {
        this.showSplashScreen();
        this.bindEvents();
        this.checkAuthStatus();
    }
    
    showSplashScreen() {
        setTimeout(() => {
            document.querySelector('.splash-screen').classList.add('hidden');
            setTimeout(() => {
                document.querySelector('.splash-screen').style.display = 'none';
            }, 500);
        }, 2000);
    }
    
    bindEvents() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => this.handleNavigation(e));
        });
        
        // Feed selector events
        document.querySelectorAll('.feed-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchFeed(e));
        });
        
        // Search events
        const searchInput = document.querySelector('.search-input');
        searchInput.addEventListener('input', this.debounce((e) => this.handleSearch(e), 300));
        
        // Modal events
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
        
        // Auth events
        document.getElementById('register-form').addEventListener('submit', (e) => this.handleRegister(e));
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('guest-btn').addEventListener('click', () => this.handleGuestLogin());
        
        // Swipe gestures for media
        this.bindSwipeEvents();
        
        // Tag management
        this.bindTagEvents();
    }
    
    bindSwipeEvents() {
        let startY = 0;
        let currentY = 0;
        let isScrolling = false;
        
        const mediaContainer = document.querySelector('.media-container');
        
        mediaContainer.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            isScrolling = true;
        });
        
        mediaContainer.addEventListener('touchmove', (e) => {
            if (!isScrolling) return;
            currentY = e.touches[0].clientY;
        });
        
        mediaContainer.addEventListener('touchend', () => {
            if (!isScrolling) return;
            
            const diffY = startY - currentY;
            
            if (Math.abs(diffY) > 50) {
                if (diffY > 0) {
                    this.nextMedia();
                } else {
                    this.previousMedia();
                }
            }
            
            isScrolling = false;
        });
    }
    
    bindTagEvents() {
        // Tag swipe events for algorithm tags
        document.addEventListener('touchstart', (e) => {
            if (e.target.classList.contains('tag-item') && e.target.classList.contains('algorithm')) {
                this.handleTagSwipe(e);
            }
        });
    }
    
    handleTagSwipe(e) {
        let startX = e.touches[0].clientX;
        let startY = e.touches[0].clientY;
        
        const handleTouchEnd = (endEvent) => {
            const endX = endEvent.changedTouches[0].clientX;
            const endY = endEvent.changedTouches[0].clientY;
            
            const diffX = endX - startX;
            const diffY = endY - startY;
            
            const tagId = e.target.dataset.tagId;
            
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 30) {
                if (diffX > 0) {
                    // Swipe right - promote tag
                    this.updateTagInterest(tagId, 'promote');
                } else {
                    // Swipe left - ignore tag
                    this.updateTagInterest(tagId, 'ignore');
                }
            } else if (diffY < -30) {
                // Swipe up - keep with lower weight
                this.updateTagInterest(tagId, 'keep');
            }
            
            document.removeEventListener('touchend', handleTouchEnd);
        };
        
        document.addEventListener('touchend', handleTouchEnd);
    }
    
    checkAuthStatus() {
        fetch('/profile')
            .then(response => response.json())
            .then(data => {
                if (data.username) {
                    this.currentUser = data;
                    this.loadFeed();
                } else {
                    this.showAuthModal();
                }
            })
            .catch(() => this.showAuthModal());
    }
    
    showAuthModal() {
        document.getElementById('auth-modal').classList.add('show');
    }
    
    hideAuthModal() {
        document.getElementById('auth-modal').classList.remove('show');
    }
    
    async handleRegister(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const selectedTags = Array.from(document.querySelectorAll('.tag-item.selected'))
            .map(tag => parseInt(tag.dataset.tagId));
        
        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            gender_preference: document.querySelector('.gender-option.selected')?.dataset.value,
            selected_tags: selectedTags
        };
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentUser = { username: data.username };
                this.hideAuthModal();
                this.loadFeed();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Registration failed');
        }
    }
    
    async handleLogin(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = {
            username: formData.get('login-username'),
            password: formData.get('login-password')
        };
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentUser = { username: data.username };
                this.hideAuthModal();
                this.loadFeed();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Login failed');
        }
    }
    
    async handleGuestLogin() {
        try {
            const response = await fetch('/guest_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentUser = { username: 'Guest', is_guest: true };
                this.hideAuthModal();
                this.loadFeed();
            }
        } catch (error) {
            this.showError('Guest login failed');
        }
    }
    
    async loadFeed() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        document.querySelector('.loading').style.display = 'block';
        
        try {
            const response = await fetch(`/feed/${this.currentFeed}?page=${this.currentPage}`);
            const data = await response.json();
            
            if (this.currentPage === 1) {
                this.mediaItems = data.media;
            } else {
                this.mediaItems.push(...data.media);
            }
            
            this.renderMedia();
            this.currentPage++;
        } catch (error) {
            this.showError('Failed to load feed');
        } finally {
            this.isLoading = false;
            document.querySelector('.loading').style.display = 'none';
        }
    }
    
    renderMedia() {
        const container = document.querySelector('.media-container');
        container.innerHTML = '';
        
        this.mediaItems.forEach((media, index) => {
            const mediaElement = this.createMediaElement(media, index);
            container.appendChild(mediaElement);
        });
        
        if (this.mediaItems.length > 0) {
            this.currentMediaIndex = 0;
            this.updateMediaVisibility();
        }
    }
    
    createMediaElement(media, index) {
        const mediaItem = document.createElement('div');
        mediaItem.className = 'media-item';
        mediaItem.dataset.index = index;
        
        let mediaContent = '';
        
        switch (media.media_type) {
            case 'video':
                mediaContent = `<video class="media-content" controls preload="metadata">
                    <source src="${media.aws_url}" type="video/mp4">
                </video>`;
                break;
            case 'image':
                mediaContent = `<img class="media-content" src="${media.aws_url}" alt="${media.title}">`;
                break;
            case 'audio':
                mediaContent = `
                    <div class="audio-player">
                        <img class="media-content" src="${media.thumbnail_url || '/static/images/audio-placeholder.jpg'}" alt="${media.title}">
                        <audio controls>
                            <source src="${media.aws_url}" type="audio/mpeg">
                        </audio>
                    </div>`;
                break;
            case 'text':
                mediaContent = `
                    <div class="text-content">
                        <h2>${media.title}</h2>
                        <div class="text-body">${media.description}</div>
                    </div>`;
                break;
            default:
                mediaContent = `<div class="placeholder">Content not supported</div>`;
        }
        
        mediaItem.innerHTML = `
            ${mediaContent}
            <div class="media-overlay">
                <h3>${media.title}</h3>
                <p>@${media.creator}</p>
                <p>${media.description}</p>
                <div class="media-tags">
                    ${media.tags.map(tag => `<span class="tag">#${tag.name}</span>`).join(' ')}
                </div>
            </div>
            <div class="media-actions">
                <button class="action-btn like-btn ${media.is_liked ? 'liked' : ''}" 
                        onclick="app.toggleLike(${media.id})">
                    ❤️
                    <div class="action-count">${media.like_count}</div>
                </button>
                <button class="action-btn save-btn ${media.is_saved ? 'saved' : ''}"
                        onclick="app.toggleSave(${media.id})">
                    🔖
                </button>
                <button class="action-btn follow-btn ${media.is_following ? 'following' : ''}"
                        onclick="app.toggleFollow(${media.creator_id})">
                    👤
                </button>
                <button class="action-btn comment-btn"
                        onclick="app.showComments(${media.id})">
                    💬
                    <div class="action-count">${media.comment_count}</div>
                </button>
            </div>
        `;
        
        return mediaItem;
    }
    
    updateMediaVisibility() {
        const items = document.querySelectorAll('.media-item');
        items.forEach((item, index) => {
            if (index === this.currentMediaIndex) {
                item.style.display = 'flex';
                // Auto-play video if it's a video
                const video = item.querySelector('video');
                if (video) {
                    video.play().catch(() => {}); // Ignore autoplay errors
                }
            } else {
                item.style.display = 'none';
                // Pause video if it's a video
                const video = item.querySelector('video');
                if (video) {
                    video.pause();
                }
            }
        });
    }
    
    nextMedia() {
        if (this.currentMediaIndex < this.mediaItems.length - 1) {
            this.currentMediaIndex++;
            this.updateMediaVisibility();
        } else if (!this.isLoading) {
            this.loadFeed(); // Load more content
        }
    }
    
    previousMedia() {
        if (this.currentMediaIndex > 0) {
            this.currentMediaIndex--;
            this.updateMediaVisibility();
        }
    }
    
    async toggleLike(mediaId) {
        try {
            const response = await fetch(`/like/${mediaId}`, { method: 'POST' });
            const result = await response.json();
            
            const btn = document.querySelector(`[onclick="app.toggleLike(${mediaId})"]`);
            const countElement = btn.querySelector('.action-count');
            
            if (result.liked) {
                btn.classList.add('liked');
            } else {
                btn.classList.remove('liked');
            }
            
            countElement.textContent = result.like_count;
        } catch (error) {
            this.showError('Failed to toggle like');
        }
    }
    
    async toggleSave(mediaId) {
        try {
            const response = await fetch(`/save/${mediaId}`, { method: 'POST' });
            const result = await response.json();
            
            const btn = document.querySelector(`[onclick="app.toggleSave(${mediaId})"]`);
            
            if (result.saved) {
                btn.classList.add('saved');
            } else {
                btn.classList.remove('saved');
            }
        } catch (error) {
            this.showError('Failed to toggle save');
        }
    }
    
    async toggleFollow(userId) {
        try {
            const response = await fetch(`/follow/${userId}`, { method: 'POST' });
            const result = await response.json();
            
            const btn = document.querySelector(`[onclick="app.toggleFollow(${userId})"]`);
            
            if (result.following) {
                btn.classList.add('following');
            } else {
                btn.classList.remove('following');
            }
        } catch (error) {
            this.showError('Failed to toggle follow');
        }
    }
    
    async showComments(mediaId) {
        try {
            const response = await fetch(`/comments/${mediaId}`);
            const data = await response.json();
            
            const modal = document.getElementById('comments-modal');
            const container = modal.querySelector('.comments-container');
            
            container.innerHTML = data.comments.map(comment => `
                <div class="comment-item">
                    <div class="comment-author">@${comment.username}</div>
                    <div class="comment-text">${comment.content}</div>
                </div>
            `).join('');
            
            // Set up comment form
            const form = modal.querySelector('.comment-form');
            form.onsubmit = (e) => this.addComment(e, mediaId);
            
            modal.classList.add('show');
        } catch (error) {
            this.showError('Failed to load comments');
        }
    }
    
    async addComment(e, mediaId) {
        e.preventDefault();
        
        const input = e.target.querySelector('.comment-input');
        const content = input.value.trim();
        
        if (!content) return;
        
        try {
            const response = await fetch(`/comment/${mediaId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            
            const result = await response.json();
            
            if (result.success) {
                input.value = '';
                this.showComments(mediaId); // Refresh comments
                
                // Update comment count in UI
                const countElement = document.querySelector(`[onclick="app.showComments(${mediaId})"] .action-count`);
                if (countElement) {
                    countElement.textContent = parseInt(countElement.textContent) + 1;
                }
            }
        } catch (error) {
            this.showError('Failed to add comment');
        }
    }
    
    switchFeed(e) {
        const feedType = e.target.dataset.feed;
        if (feedType === this.currentFeed) return;
        
        document.querySelectorAll('.feed-tab').forEach(tab => tab.classList.remove('active'));
        e.target.classList.add('active');
        
        this.currentFeed = feedType;
        this.currentPage = 1;
        this.loadFeed();
    }
    
    handleNavigation(e) {
        const navType = e.currentTarget.dataset.nav;
        
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        e.currentTarget.classList.add('active');
        
        switch (navType) {
            case 'liked':
                this.showLikedMedia();
                break;
            case 'saved':
                this.showSavedMedia();
                break;
            case 'profile':
                this.showProfile();
                break;
            default:
                this.loadFeed();
        }
    }
    
    async showProfile() {
        try {
            const response = await fetch('/profile');
            const data = await response.json();
            
            const modal = document.getElementById('profile-modal');
            const selectedTagsContainer = modal.querySelector('#selected-tags');
            const algorithmTagsContainer = modal.querySelector('#algorithm-tags');
            
            selectedTagsContainer.innerHTML = data.selected_tags.map(tag => `
                <div class="tag-item selected" data-tag-id="${tag.id}" ondblclick="app.editTag(${tag.id})">
                    ${tag.name}
                </div>
            `).join('');
            
            algorithmTagsContainer.innerHTML = data.algorithm_tags.map(tag => `
                <div class="tag-item algorithm ${tag.interest_level < 0.5 ? 'weak' : ''}" 
                     data-tag-id="${tag.id}">
                    ${tag.name}
                </div>
            `).join('');
            
            modal.classList.add('show');
        } catch (error) {
            this.showError('Failed to load profile');
        }
    }
    
    async updateTagInterest(tagId, action) {
        try {
            await fetch('/update_tag_interest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag_id: tagId, action })
            });
            
            // Refresh profile to show changes
            this.showProfile();
        } catch (error) {
            this.showError('Failed to update tag');
        }
    }
    
    async handleSearch(e) {
        const query = e.target.value.trim();
        if (!query) return;
        
        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            // Display search results (implement search results UI)
            console.log('Search results:', data.results);
        } catch (error) {
            this.showError('Search failed');
        }
    }
    
    closeModal() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('show');
        });
    }
    
    showError(message) {
        // Create and show error toast
        const toast = document.createElement('div');
        toast.className = 'error';
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.zIndex = '10001';
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
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
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new TikTokClone();
});