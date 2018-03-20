import React from 'react'
import Link from 'gatsby-link'

const Header = () => (
  <header
    className="header grid__item w-full md-w-1/2"
    style={{
      backgroundColor: '#6536c0',
      padding: '50px'
    }}
  >
    <div
      style={{
        margin: '0 auto',
        height: '100%',
        width: '100%'
      }}
    >
      <h1 style={{ marginBottom: '16px' }}>
        <Link
          to="/"
          style={{
            color: 'white',
            textDecoration: 'none',
          }}
        >
          <img className="avatar" src="images/profile.jpg" alt="Profile picture" /><br/>
          Juan Sebastián Visbal
        </Link>
      </h1>
      <h3 style={{ marginBottom: '16px' }}>Electronics & Web Engineer</h3>
      <div style={{ marginBottom: '16px' }}>
        <button id="contactMe" className="btn uppercase">Contact me</button>
      </div>
    </div>
  </header>
)

export default Header
