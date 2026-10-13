// og_image returns the absolute URL of a page's link-preview image: a post's first photo
// (`image` in data.blog.posts), else its generated card /og/<page path>.png, which
// tools/build_extras.py draws after the build.
//
// usage: ${ og_image(data.blog.posts, page.path, site.base_url) }
export default function og_image(posts, path, base) {
    path = path || "/";
    const post = Array.isArray(posts) ? posts.find((p) => p.path === path) : null;
    let src = post && post.image ? post.image : card(path);
    if (src.startsWith("/") && !src.startsWith("//")) src = String(base || "").replace(/\/$/, "") + src;
    return src;
}

// "/" -> "/og/index.png", "/now.html" -> "/og/now.png", "/blog/" -> "/og/blog/index.png"
function card(path) {
    return "/og" + (path.endsWith("/") ? path + "index" : path.replace(/\.html$/, "")) + ".png";
}
