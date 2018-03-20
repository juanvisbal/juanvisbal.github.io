const autoprefixer = require('autoprefixer');

module.exports = {
  siteMetadata: {
    title: 'Gatsby Default Starter',
  },
  plugins: [
    'gatsby-plugin-react-helmet',
    {
      resolve: 'gatsby-plugin-postcss-sass',
      options: {
        postCssPlugins: [
          autoprefixer({
            browsers: ['last 2 versions']
          })
        ],
        precision: 8, // SASS default: 5
      },
    },
  ],
};
