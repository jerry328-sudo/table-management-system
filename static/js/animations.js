// 流畅动画和交互效果

// 页面加载时的动画
document.addEventListener('DOMContentLoaded', function() {
    // 添加页面加载动画
    animateOnLoad();
    
    // 添加滚动动画
    setupScrollAnimations();
    
    // 添加进度条动画增强
    enhanceProgressBars();
    
    // 添加卡片悬停效果
    setupCardInteractions();
    
    // 添加按钮点击效果
    setupButtonEffects();
});

// 页面加载动画
function animateOnLoad() {
    const cards = document.querySelectorAll('.card');
    const navbar = document.querySelector('.navbar');
    
    // 导航栏从上方滑入
    if (navbar) {
        navbar.style.transform = 'translateY(-100%)';
        navbar.style.opacity = '0';
        
        setTimeout(() => {
            navbar.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            navbar.style.transform = 'translateY(0)';
            navbar.style.opacity = '1';
        }, 100);
    }
    
    // 卡片依次从下方滑入
    cards.forEach((card, index) => {
        card.style.transform = 'translateY(50px)';
        card.style.opacity = '0';
        
        setTimeout(() => {
            card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.transform = 'translateY(0)';
            card.style.opacity = '1';
        }, 200 + index * 150);
    });
}

// 滚动动画设置
function setupScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // 观察所有需要动画的元素
    const animateElements = document.querySelectorAll('.card, .alert, .form-container');
    animateElements.forEach(el => {
        observer.observe(el);
    });
}

// 增强进度条动画
function enhanceProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        const originalWidth = bar.style.width;
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.transition = 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)';
            bar.style.width = originalWidth;
        }, 500);
        
        // 添加数值计数动画
        const textElement = bar.parentElement.previousElementSibling;
        if (textElement && textElement.textContent.includes('/')) {
            animateCountUp(textElement, originalWidth);
        }
    });
}

// 数值计数动画
function animateCountUp(element, targetWidth) {
    const text = element.textContent;
    const match = text.match(/(\d+)\/(\d+)/);
    
    if (match) {
        const current = parseInt(match[1]);
        const total = parseInt(match[2]);
        const prefix = text.split(match[0])[0];
        const suffix = text.split(match[0])[1];
        
        let counter = 0;
        const increment = current / 30; // 30帧动画
        
        const timer = setInterval(() => {
            counter += increment;
            if (counter >= current) {
                counter = current;
                clearInterval(timer);
            }
            
            const remaining = total - Math.floor(counter);
            element.textContent = `${prefix}${Math.floor(counter)}/${total} (剩余: ${remaining})${suffix}`;
        }, 50);
    }
}

// 卡片交互效果
function setupCardInteractions() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        // 鼠标进入时的倾斜效果
        card.addEventListener('mouseenter', function(e) {
            this.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        });
        
        // 鼠标移动时的3D效果
        card.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;
            
            this.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
        });
        
        // 鼠标离开时重置
        card.addEventListener('mouseleave', function() {
            this.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            this.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
        });
    });
}

// 按钮效果增强
function setupButtonEffects() {
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(button => {
        // 点击波纹效果
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// 进度条实时更新动画
function animateProgressUpdate(progressBar, newWidth) {
    if (!progressBar) return;
    
    const currentWidth = parseFloat(progressBar.style.width) || 0;
    const targetWidth = parseFloat(newWidth);
    
    if (Math.abs(targetWidth - currentWidth) < 0.1) return;
    
    progressBar.style.transition = 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
    progressBar.style.width = newWidth;
    
    // 添加临时高亮效果
    progressBar.classList.add('updating');
    setTimeout(() => {
        progressBar.classList.remove('updating');
    }, 800);
}

// 页面切换动画
function pageTransition(targetUrl) {
    const body = document.body;
    body.style.transition = 'opacity 0.3s ease-out';
    body.style.opacity = '0';
    
    setTimeout(() => {
        window.location.href = targetUrl;
    }, 300);
}

// 添加页面切换动画到导航链接
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link[href^="/"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            pageTransition(this.href);
        });
    });
});

// 自适应动画（减少动画在移动设备上的复杂度）
function setupResponsiveAnimations() {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    
    function handleMediaChange(e) {
        const cards = document.querySelectorAll('.card');
        
        if (e.matches) {
            // 移动设备：简化动画
            cards.forEach(card => {
                card.addEventListener('mousemove', null);
                card.style.transform = '';
            });
        } else {
            // 桌面设备：完整动画
            setupCardInteractions();
        }
    }
    
    mediaQuery.addListener(handleMediaChange);
    handleMediaChange(mediaQuery);
}

// 初始化响应式动画
document.addEventListener('DOMContentLoaded', setupResponsiveAnimations);

// 添加CSS动画类
const style = document.createElement('style');
style.textContent = `
    .animate-in {
        animation: slideInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        transform: scale(0);
        animation: rippleEffect 0.6s linear;
        background-color: rgba(255, 255, 255, 0.3);
        pointer-events: none;
    }
    
    @keyframes rippleEffect {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .progress-bar.updating {
        box-shadow: 0 0 10px rgba(13, 110, 253, 0.5);
        filter: brightness(1.2);
    }
    
    body {
        transition: opacity 0.3s ease-out;
    }
`;

document.head.appendChild(style);