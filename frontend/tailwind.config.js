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
          neutral: '#4c4c4c', // navbar & footer
          'base-100': '#131518', // input & content bg
          'base-200': '#131518', // border & special content bg
          'base-300': '#212529', // background
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