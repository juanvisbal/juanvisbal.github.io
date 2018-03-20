import React from 'react'
import PropTypes from 'prop-types'
import Helmet from 'react-helmet'

import Header from '../components/Header'
import './index.scss'

let locales = ['en']

const TemplateWrapper = ({ children }) => (
  <div className="container">
    <Helmet
      title='JV Soluciones para PYMs'
      titleAttributes={{itemprop: "name", lang: "es"}}
      htmlAttributes={{lang: 'es'}}
      meta={[
        { name: 'description', content: 'Soluciones tecnológicas para PYMs' },
        { name: 'keywords', content: 'sample, something' },
        { name: 'theme-color', content: '#e8f5e9' }
      ]}
    >
      <link rel="icon" href="images/js-xxl.png" size="192x192"/>
      {locales.map((locale) => {
        <link rel="alternate" href="http://example.com/{locale}" hrefLang={locale} />
      })}
    </Helmet>

    <div className="content grid">
      <Header />

      <main
        className="main grid__item w-full md-w-1/2"
        role="main"
        style={{
          backgroundColor: '#fff',
          margin: '0 auto',
          padding: '50px',
        }}
      >
        {children()}
      </main>
    </div>
  </div>
)

TemplateWrapper.propTypes = {
  children: PropTypes.func,
}

export default TemplateWrapper
