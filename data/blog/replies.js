// data.blog.replies: the replies from every data/blog/replies_YYYY.json (Micro.blog exports),
// newest first.
export default function replies() {
    const items = [];
    for (const [name, feed] of Object.entries(data.blog || {})) {
        if (name.startsWith("replies_") && feed && Array.isArray(feed.items)) items.push(...feed.items);
    }
    return items.sort((a, b) => Date.parse(b.date_published) - Date.parse(a.date_published));
}
