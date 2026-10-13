// data.home: the home page's front matter (bio, links, elsewhere), for /about and /contact.
export default function home() {
    return site.pages.find((p) => p.path === "/") || {};
}
