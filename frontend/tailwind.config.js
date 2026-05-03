/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: 'var(--color-primary)',
          secondary: 'var(--color-secondary)',
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          danger: 'var(--color-danger)',
          info: 'var(--color-info)',
        },
        surface: {
          base: 'var(--color-bg-base)',
          primary: 'var(--color-surface-primary)',
          secondary: 'var(--color-surface-secondary)',
        },
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          disabled: 'var(--color-text-disabled)',
        },
        border: {
          DEFAULT: 'var(--color-border-default)',
          strong: 'var(--color-border-strong)',
        },
        // Role accent tokens
        role: {
          customer: 'var(--role-customer)',
          'customer-soft': 'var(--role-customer-soft)',
          admin: 'var(--role-admin)',
          'admin-soft': 'var(--role-admin-soft)',
          teller: 'var(--role-teller)',
          'teller-soft': 'var(--role-teller-soft)',
          risk: 'var(--role-risk)',
          'risk-soft': 'var(--role-risk-soft)',
          cs: 'var(--role-cs)',
          'cs-soft': 'var(--role-cs-soft)',
        },
        sidebar: {
          bg: 'var(--sidebar-bg)',
        },
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
      },
    },
  },
  plugins: [],
}

