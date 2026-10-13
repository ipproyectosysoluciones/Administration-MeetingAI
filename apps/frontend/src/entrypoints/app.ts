// Main client-side entry point for ReunionAI frontend
import '../styles/global.css';

// Theme initialization
function initTheme(): void {
  const theme = localStorage.getItem('theme') || 'system';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && prefersDark);
  document.documentElement.classList.toggle('dark', isDark);
}

// Password visibility toggle
function initPasswordToggle(): void {
  document.querySelectorAll('[id^="toggle-password"]').forEach(button => {
    button.addEventListener('click', () => {
      const input = button.parentElement?.querySelector('input[type="password"], input[type="text"]') as HTMLInputElement;
      const eyeOpen = button.querySelector('#eye-open');
      const eyeClosed = button.querySelector('#eye-closed');

      if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        eyeOpen?.classList.toggle('hidden', !isPassword);
        eyeClosed?.classList.toggle('hidden', isPassword);
      }
    });
  });
}

// Form validation
function initFormValidation(): void {
  document.querySelectorAll('form[novalidate]').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
      const btnText = submitBtn.querySelector('#btn-text') as HTMLElement;
      const btnLoader = submitBtn.querySelector('#btn-loader') as HTMLElement;

      // Clear previous errors
      form.querySelectorAll('[id$="-error"]').forEach(el => {
        (el as HTMLElement).classList.add('hidden');
        el.textContent = '';
      });

      // Validate required fields
      let isValid = true;
      const requiredFields = form.querySelectorAll('[required]');

      requiredFields.forEach(field => {
        const input = field as HTMLInputElement;
        if (!input.value.trim()) {
          isValid = false;
          showError(input, 'Este campo es obligatorio');
        } else if (input.type === 'email' && !isValidEmail(input.value)) {
          isValid = false;
          showError(input, 'Correo electrónico inválido');
        } else if (input.type === 'password' && input.id === 'confirm_password') {
          const password = document.getElementById('password') as HTMLInputElement;
          if (input.value !== password?.value) {
            isValid = false;
            showError(input, 'Las contraseñas no coinciden');
          }
        } else if (input.id === 'password' && input.value.length < 8) {
          isValid = false;
          showError(input, 'La contraseña debe tener al menos 8 caracteres');
        }
      });

      if (!isValid) return;

      // Show loading state
      submitBtn.disabled = true;
      btnText?.classList.add('hidden');
      btnLoader?.classList.remove('hidden');

      // Submit form
      try {
        const formData = new FormData(form);
        const response = await fetch(form.action || window.location.pathname, {
          method: form.method || 'POST',
          body: formData,
          headers: {
            'Accept': 'application/json',
          },
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.message || 'Error en la solicitud');
        }

        // Success - redirect or show success
        if (data.redirect) {
          window.location.href = data.redirect;
        } else {
          window.location.reload();
        }
      } catch (error) {
        console.error('Form error:', error);
        alert(error instanceof Error ? error.message : 'Error desconocido');
      } finally {
        submitBtn.disabled = false;
        btnText?.classList.remove('hidden');
        btnLoader?.classList.add('hidden');
      }
    });
  });
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showError(input: HTMLInputElement, message: string): void {
  const errorEl = document.getElementById(`${input.id}-error`);
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
  }
  input.classList.add('border-red-500', 'focus:border-red-500', 'focus:ring-red-500/20');
}

// Password strength meter
function initPasswordStrength(): void {
  const passwordInput = document.getElementById('password') as HTMLInputElement;
  if (!passwordInput) return;

  const strengthBar = document.createElement('div');
  strengthBar.className = 'mt-1 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden';
  strengthBar.innerHTML = '<div id="password-strength-bar" class="h-full bg-gray-300 dark:bg-gray-600 transition-all duration-300" style="width: 0%"></div>';
  passwordInput.parentElement?.appendChild(strengthBar);

  passwordInput.addEventListener('input', () => {
    const strength = calculatePasswordStrength(passwordInput.value);
    const bar = document.getElementById('password-strength-bar') as HTMLElement;
    if (bar) {
      bar.style.width = `${strength.percent}%`;
      bar.className = `h-full transition-all duration-300 ${strength.color}`;
    }
  });
}

function calculatePasswordStrength(password: string): { percent: number; color: string } {
  let score = 0;
  if (password.length >= 8) score += 25;
  if (password.length >= 12) score += 15;
  if (/[A-Z]/.test(password)) score += 20;
  if (/[a-z]/.test(password)) score += 10;
  if (/[0-9]/.test(password)) score += 15;
  if (/[^A-Za-z0-9]/.test(password)) score += 15;

  if (score < 30) return { percent: 25, color: 'bg-red-500' };
  if (score < 50) return { percent: 50, color: 'bg-yellow-500' };
  if (score < 75) return { percent: 75, color: 'bg-yellow-500' };
  return { percent: 100, color: 'bg-green-500' };
}

// Slug auto-generation
function initSlugGeneration(): void {
  const nameInput = document.getElementById('organization_name') as HTMLInputElement;
  const slugInput = document.getElementById('organization_slug') as HTMLInputElement;

  if (!nameInput || !slugInput) return;

  let userEdited = false;

  nameInput.addEventListener('input', () => {
    if (!userEdited) {
      slugInput.value = nameInput.value
        .toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Remove accents
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .substring(0, 50);
    }
  });

  slugInput.addEventListener('input', () => {
    userEdited = true;
  });
}

// Theme toggle
function initThemeToggle(): void {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;

  themeToggle.addEventListener('click', () => {
    document.documentElement.classList.toggle('dark');
    const isDark = document.documentElement.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
}

// Initialize all
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initPasswordToggle();
  initFormValidation();
  initPasswordStrength();
  initSlugGeneration();
  initThemeToggle();

  // Add global styles for form errors
  const style = document.createElement('style');
  style.textContent = `
    input.border-red-500:focus {
      --tw-ring-color: #ef4444;
    }
  `;
  document.head.appendChild(style);
});