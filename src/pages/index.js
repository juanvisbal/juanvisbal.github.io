import React from 'react'
import Link from 'gatsby-link'

const IndexPage = () => (
  <div>
    <h2>About me</h2>
    <p>
    I'm an Electronics Engineer from Barranquilla, Colombia. I currently work as an independent web developer, creating websites for small businesses, and as support engineer at <a href="https://www.pasilobus.com">Pasilobus, Inc.</a>
    </p>
    <p>Some things to know about me: I'm a UX enthusiast, and aspring entrepreneur. A hard worker, I'm highly organized, good at delegating and teammwork but also independent, very eager to learn and obtain experience.
    </p>
    <a class="resume btn uppercase waves-effect" href="JSV-Resume.pdf">Download Resumé</a>
    <Link to="/page-2/">Go to page 2</Link>
  </div>
)

export default IndexPage
