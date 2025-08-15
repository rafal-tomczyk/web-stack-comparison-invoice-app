   module.exports = {
     content: [
       '../templates/**/*.html',
       '../../**/templates/**/*.html',
       '../../**/static/**/*.js',
     ],
       darkMode: false,
     theme: {
       extend: {},
     },
     plugins: [
       require('daisyui')
     ],
       daisyui: {
    themes: ["magisterka"],
    darkTheme: null,
  },

   }
