// Основной JavaScript файл

$(document).ready(function() {
    // Инициализация всплывающих подсказок
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Инициализация всплывающих окон
    $('[data-bs-toggle="popover"]').popover();
    
    // Плавная прокрутка для якорных ссылок
    $('a[href^="#"]').on('click', function(e) {
        if (this.hash !== "") {
            e.preventDefault();
            
            const hash = this.hash;
            $('html, body').animate({
                scrollTop: $(hash).offset().top - 80
            }, 800);
        }
    });
    
    // Динамическое обновление формы при изменении
    $('select').on('change', function() {
        $(this).removeClass('is-invalid');
    });
    
    $('input[type="text"], input[type="email"], textarea').on('input', function() {
        $(this).removeClass('is-invalid');
    });
    
    // Обработка форм с подтверждением
    $('form[data-confirm]').on('submit', function(e) {
        const message = $(this).data('confirm');
        if (!confirm(message)) {
            e.preventDefault();
        }
    });
    
    // Автоматическое скрытие alert через 5 секунд
    setTimeout(function() {
        $('.alert:not(.alert-permanent)').fadeOut(500, function() {
            $(this).remove();
        });
    }, 5000);
    
    // Управление видимостью пароля
    $('.toggle-password').on('click', function() {
        const target = $(this).data('target');
        const input = $(target);
        const icon = $(this).find('i');
        
        if (input.attr('type') === 'password') {
            input.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            input.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
    
    // AJAX CSRF токен для всех запросов
    $.ajaxSetup({
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
    
    // Утилита для получения CSRF токена
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Проверка онлайн-статуса
    window.addEventListener('online', function() {
        showToast('Соединение восстановлено', 'success');
    });
    
    window.addEventListener('offline', function() {
        showToast('Отсутствует подключение к интернету', 'warning');
    });
    
    // Функция для показа уведомлений
    window.showToast = function(message, type = 'info') {
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        $('.toast-container').append(toastHtml);
        const toast = new bootstrap.Toast(document.getElementById(toastId));
        toast.show();
        
        // Удаляем toast после скрытия
        $(`#${toastId}`).on('hidden.bs.toast', function() {
            $(this).remove();
        });
    };
    
    // Инициализация тултипов Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Глобальные утилиты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function debounce(func, wait) {
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

// Экспорт функций для использования в других файлах
window.utils = {
    formatDate,
    formatDateTime,
    debounce
};