module.exports = {
  mode: 'jit',
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  daisyui: {
    themes: [
      'light',
      'dark',
      'forest',
      {
        'downtify-dark': {
          // ...require('daisyui/src/colors/themes')['[data-theme=forest]'],
          primary: '#1AD05C', // downtify green
          'primary-content': '#ffffff', // font color on primary
          secondary: '#ffffff', // unused?
          accent: '#ffffff', // unused
          neutral: '#121212', // navbar & footer
          'base-100': '#1F1F1F', // input & content bg
          'base-200': '#1F1F1F', // border & special content bg
          'base-300': '#000000', // background
          info: '#3ABFF8',
          success: '#1AD05C',
          warning: '#FBBD23',
          error: '#F87272',
          '--rounded-btn': '1.9rem',
        },
      },
      {
        'downtify-light': {
          primary: '#1AD05C',
          'primary-content': '#ffffff',
          secondary: '#5d5d5d',
          accent: '#16ce57',
          neutral: '#4c4c4c',
          'base-100': '#ffffff',
          'base-200': '#ffffff',
          'base-300': '#ffffff',
          info: '#3ABFF8',
          success: '#1AD05C',
          warning: '#FBBD23',
          error: '#F87272',
          '--rounded-btn': '1.9rem',
        },
      },
    ],
  },
  plugins: [require('daisyui')],
}